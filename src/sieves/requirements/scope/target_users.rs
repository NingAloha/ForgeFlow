use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Write};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::mutation::operations::{apply_operations, OperationSet};
use crate::sieves::requirements::artifact::{
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::{
    load_requirements,
    save_requirements,
};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/target_users_question_system.txt");

const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/target_users_extract_system.txt");

const TARGET_USERS_CLARIFICATION_ID: &str = "product.target_users";

const TARGET_USERS_ALLOWED_PATHS: &[&[&str]] = &[
    &["product", "target_users"],
];

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

pub fn run_target_users_scope() -> Result<()> {
    let artifact = load_requirements()
        .context("failed to load requirements artifact")?;

    let clarification = find_pending_clarification(
        &artifact,
        TARGET_USERS_CLARIFICATION_ID,
    )?;

    let generated_question = generate_target_users_question(
        &artifact,
        &clarification,
    )?;

    println!("Current question:");
    println!("{generated_question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact = update_target_users(
        artifact,
        &clarification,
        answer.trim(),
    )?;

    save_requirements(&updated_artifact)
        .context("failed to save requirements artifact")?;

    println!();
    println!("Saved requirements artifact:");
    println!("{}", serde_json::to_string_pretty(&updated_artifact)?);

    Ok(())
}

fn generate_target_users_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.product.target_users,
        "relevant_context": {
            "intent": artifact.intent
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate target users clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated target users question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_target_users(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before target users update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.product.target_users,
        "relevant_context": {
            "intent": artifact.intent
        }
    });

    let operation_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract target users operations")?;

    let operation_set: OperationSet = serde_json::from_value(operation_value)
        .context("LLM JSON does not match OperationSet schema")?;

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    apply_operations(
        &mut artifact_value,
        &operation_set,
        TARGET_USERS_ALLOWED_PATHS,
    )
    .context("failed to apply target users operations")?;

    remove_pending_clarification_by_id(
        &mut artifact_value,
        TARGET_USERS_CLARIFICATION_ID,
    )?;

    set_value_at_path(
        &mut artifact_value,
        &["maturity".to_string()],
        Value::String("scope".to_string()),
    )
    .context("failed to set maturity after target users update")?;

    let updated_artifact: RequirementsArtifact =
        serde_json::from_value(artifact_value)
            .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("target users update produced invalid requirements artifact")?;

    validate_target_users_result(&updated_artifact)?;

    Ok(updated_artifact)
}

fn find_pending_clarification(
    artifact: &RequirementsArtifact,
    id: &str,
) -> Result<PendingClarification> {
    artifact
        .pending_clarifications
        .iter()
        .find(|item| item.id == id)
        .cloned()
        .ok_or_else(|| anyhow!("pending clarification {:?} not found", id))
}

fn remove_pending_clarification_by_id(
    artifact_value: &mut Value,
    id: &str,
) -> Result<()> {
    let pending = artifact_value
        .get_mut("pending_clarifications")
        .and_then(Value::as_array_mut)
        .ok_or_else(|| anyhow!("pending_clarifications must be an array"))?;

    let original_len = pending.len();

    pending.retain(|item| {
        item.get("id")
            .and_then(Value::as_str)
            != Some(id)
    });

    if pending.len() == original_len {
        anyhow::bail!(
            "pending clarification {:?} was not removed because it was not found",
            id
        );
    }

    Ok(())
}

fn validate_target_users_result(artifact: &RequirementsArtifact) -> Result<()> {
    if artifact.product.target_users.is_empty() {
        anyhow::bail!("target users update must populate product.target_users");
    }

    if artifact
        .pending_clarifications
        .iter()
        .any(|item| item.id == TARGET_USERS_CLARIFICATION_ID)
    {
        anyhow::bail!(
            "target users pending clarification must be removed after successful update"
        );
    }

    Ok(())
}