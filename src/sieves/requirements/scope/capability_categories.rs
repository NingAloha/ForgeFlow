use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Write};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::sieves::requirements::artifact::{
    Inconsistency,
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::{load_requirements, save_requirements};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/capability_categories_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/capability_categories_extract_system.txt");
const CAPABILITY_CATEGORIES_CLARIFICATION_ID: &str =
    "scope.capability_categories";
const CAPABILITY_CATEGORIES_SIEVE_ID: &str =
    "requirements.scope.capability_categories";

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct CapabilityCategoriesExtraction {
    capability_categories: Vec<String>,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_capability_categories_scope() -> Result<()> {
    let artifact = load_requirements().context("failed to load requirements artifact")?;

    let clarification = find_pending_clarification(
        &artifact,
        CAPABILITY_CATEGORIES_CLARIFICATION_ID,
    )?;

    let question = generate_capability_categories_question(&artifact, &clarification)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact =
        update_capability_categories(artifact, &clarification, answer.trim())?;

    save_requirements(&updated_artifact).context("failed to save requirements artifact")?;

    println!();
    println!("Saved requirements artifact:");
    println!("{}", serde_json::to_string_pretty(&updated_artifact)?);

    Ok(())
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

fn generate_capability_categories_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.scope.capability_categories,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate capability categories clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated capability categories question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_capability_categories(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before capability categories update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.scope.capability_categories,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract capability categories")?;

    let extraction: CapabilityCategoriesExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match CapabilityCategoriesExtraction schema")?;

    apply_capability_categories_extraction(artifact, &extraction)
}

fn apply_capability_categories_extraction(
    artifact: RequirementsArtifact,
    extraction: &CapabilityCategoriesExtraction,
) -> Result<RequirementsArtifact> {
    validate_capability_categories_extraction(extraction)?;

    if extraction.capability_categories.is_empty()
        && extraction.detected_inconsistencies.is_empty()
    {
        anyhow::bail!(
            "capability categories answer did not clarify capability_categories"
        );
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.capability_categories.is_empty() {
        set_value_at_path(
            &mut artifact_value,
            &["scope".to_string(), "capability_categories".to_string()],
            serde_json::to_value(&extraction.capability_categories)
                .context("failed to serialize capability_categories")?,
        )
        .context("failed to set scope.capability_categories")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            let built = build_capability_categories_inconsistency(detected)?;
            inconsistencies.push(
                serde_json::to_value(built)
                    .context("failed to serialize inconsistency")?,
            );
        }
    }

    set_value_at_path(
        &mut artifact_value,
        &["maturity".to_string()],
        Value::String("scope".to_string()),
    )
    .context("failed to set maturity after capability categories update")?;

    if !extraction.capability_categories.is_empty()
        && extraction.detected_inconsistencies.is_empty()
    {
        let _removed = remove_pending_clarification_by_id(
            &mut artifact_value,
            CAPABILITY_CATEGORIES_CLARIFICATION_ID,
        )?;
    }

    let updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("capability categories update produced invalid requirements artifact")?;

    validate_capability_categories_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn validate_capability_categories_extraction(
    extraction: &CapabilityCategoriesExtraction,
) -> Result<()> {
    for (index, item) in extraction.capability_categories.iter().enumerate() {
        if item.trim().is_empty() {
            anyhow::bail!("capability_categories[{index}] must not be empty");
        }
    }

    for (index, item) in extraction.detected_inconsistencies.iter().enumerate() {
        if item.id.trim().is_empty() {
            anyhow::bail!("detected_inconsistencies[{index}].id must not be empty");
        }
        if item.message.trim().is_empty() {
            anyhow::bail!(
                "detected_inconsistencies[{index}].message must not be empty"
            );
        }
    }

    Ok(())
}

fn build_capability_categories_inconsistency(
    detected: &DetectedInconsistency,
) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.capability_categories.{}", detected.id),
        stage: "scope".to_string(),
        sieve: CAPABILITY_CATEGORIES_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec![
            "scope".to_string(),
            "capability_categories".to_string(),
        ]],
        message: detected.message.clone(),
        requires_clarification: true,
    })
}

fn remove_pending_clarification_by_id(
    artifact_value: &mut Value,
    id: &str,
) -> Result<bool> {
    let pending = artifact_value
        .get_mut("pending_clarifications")
        .and_then(Value::as_array_mut)
        .ok_or_else(|| anyhow!("pending_clarifications must be an array"))?;

    let original_len = pending.len();
    pending.retain(|item| item.get("id").and_then(Value::as_str) != Some(id));

    Ok(pending.len() != original_len)
}

fn validate_capability_categories_result(
    artifact: &RequirementsArtifact,
    extraction: &CapabilityCategoriesExtraction,
) -> Result<()> {
    if !extraction.capability_categories.is_empty()
        && artifact.scope.capability_categories.is_empty()
    {
        anyhow::bail!(
            "capability categories update must populate scope.capability_categories"
        );
    }

    let has_pending = artifact.pending_clarifications.iter().any(|item| {
        item.id == CAPABILITY_CATEGORIES_CLARIFICATION_ID
    });

    if extraction.detected_inconsistencies.is_empty()
        && !extraction.capability_categories.is_empty()
        && has_pending
    {
        anyhow::bail!(
            "capability_categories pending clarification must be removed after successful update"
        );
    }

    if !extraction.detected_inconsistencies.is_empty() && !has_pending {
        anyhow::bail!(
            "capability_categories pending clarification must remain when inconsistencies exist"
        );
    }

    if !extraction.detected_inconsistencies.is_empty()
        && !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == CAPABILITY_CATEGORIES_SIEVE_ID)
    {
        anyhow::bail!(
            "capability categories inconsistencies must be appended with matching sieve"
        );
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sieves::requirements::artifact::{Intent, Product, Scope};

    fn base_artifact() -> RequirementsArtifact {
        RequirementsArtifact {
            artifact_type: "requirements".to_string(),
            schema_version: "0.1".to_string(),
            maturity: "intent".to_string(),
            intent: Intent {
                raw_input: "设计一个ide".to_string(),
                goal: "设计一个集成开发环境".to_string(),
                domain: "软件开发工具".to_string(),
            },
            product: Product {
                target_users: vec!["学生".to_string()],
                application_type: vec!["桌面应用".to_string()],
                target_platforms: vec!["macOS".to_string()],
            },
            scope: Scope {
                capability_categories: vec![],
                mandatory_constraints: vec![],
                scope_exclusions: vec![],
            },
            functional_requirements: vec![],
            non_functional_requirements: vec![],
            external_interfaces: vec![],
            data_requirements: vec![],
            pending_clarifications: vec![PendingClarification {
                id: CAPABILITY_CATEGORIES_CLARIFICATION_ID.to_string(),
                target_path: vec![
                    "scope".to_string(),
                    "capability_categories".to_string(),
                ],
                question: "核心能力类别有哪些？".to_string(),
                sieve: CAPABILITY_CATEGORIES_SIEVE_ID.to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn explicit_categories_pass_and_remove_pending() {
        let artifact = base_artifact();
        let extraction = CapabilityCategoriesExtraction {
            capability_categories: vec![
                "代码编辑".to_string(),
                "运行与调试".to_string(),
            ],
            detected_inconsistencies: vec![],
        };

        let updated = apply_capability_categories_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert_eq!(
            updated.scope.capability_categories,
            vec!["代码编辑".to_string(), "运行与调试".to_string()]
        );
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == CAPABILITY_CATEGORIES_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn grouped_result_update_path_supported() {
        let artifact = base_artifact();
        let extraction = CapabilityCategoriesExtraction {
            capability_categories: vec![
                "代码编辑".to_string(),
                "运行与调试".to_string(),
                "版本控制集成".to_string(),
            ],
            detected_inconsistencies: vec![],
        };

        let updated = apply_capability_categories_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert_eq!(updated.scope.capability_categories.len(), 3);
    }

    #[test]
    fn implementation_details_produce_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = CapabilityCategoriesExtraction {
            capability_categories: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "implementation_details_in_capability_categories".to_string(),
                message: "用户回答主要描述技术实现，而不是产品能力类别，需要重新澄清能力边界。".to_string(),
            }],
        };

        let updated = apply_capability_categories_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated.scope.capability_categories.is_empty());
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == CAPABILITY_CATEGORIES_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| item.sieve == CAPABILITY_CATEGORIES_SIEVE_ID)
            .expect("must have inconsistency");
        assert_eq!(inconsistency.severity, "blocking");
    }

    #[test]
    fn ambiguous_capability_produces_blocking_inconsistency_and_keeps_pending() {
        let artifact = base_artifact();
        let extraction = CapabilityCategoriesExtraction {
            capability_categories: vec![],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "ambiguous_capability_category".to_string(),
                message: "用户回答中的能力类别过于宽泛，需要进一步澄清具体能力边界。".to_string(),
            }],
        };

        let updated = apply_capability_categories_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == CAPABILITY_CATEGORIES_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.id == "scope.capability_categories.ambiguous_capability_category"));
    }

    #[test]
    fn mixed_extraction_keeps_pending_when_inconsistency_exists() {
        let artifact = base_artifact();
        let extraction = CapabilityCategoriesExtraction {
            capability_categories: vec!["代码编辑".to_string()],
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "ambiguous_capability_category".to_string(),
                message: "部分能力边界过于宽泛，需要进一步澄清。".to_string(),
            }],
        };

        let updated = apply_capability_categories_extraction(artifact, &extraction)
            .expect("update should succeed");

        assert_eq!(updated.scope.capability_categories, vec!["代码编辑".to_string()]);
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == CAPABILITY_CATEGORIES_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == CAPABILITY_CATEGORIES_SIEVE_ID));
    }

    #[test]
    fn empty_extraction_rejected() {
        let artifact = base_artifact();
        let extraction = CapabilityCategoriesExtraction {
            capability_categories: vec![],
            detected_inconsistencies: vec![],
        };

        let err = apply_capability_categories_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert_eq!(
            err.to_string(),
            "capability categories answer did not clarify capability_categories"
        );
    }
}
