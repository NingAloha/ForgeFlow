use anyhow::{anyhow, Context, Result};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Write};

use crate::llm;
use crate::mutation::json_write::set_value_at_path;
use crate::sieves::requirements::artifact::{
    Inconsistency,
    ScopeExclusion,
    PendingClarification,
    RequirementsArtifact,
};
use crate::sieves::requirements::io::{load_requirements, save_requirements};
use crate::sieves::requirements::validator::validate_requirements_artifact;

const QUESTION_SYSTEM_PROMPT: &str =
    include_str!("prompts/scope_exclusions_question_system.txt");
const EXTRACT_SYSTEM_PROMPT: &str =
    include_str!("prompts/scope_exclusions_extract_system.txt");
const SCOPE_EXCLUSIONS_CLARIFICATION_ID: &str = "scope.scope_exclusions";
const SCOPE_EXCLUSIONS_SIEVE_ID: &str = "requirements.scope.scope_exclusions";

#[derive(Debug, Deserialize)]
struct ClarificationQuestion {
    question: String,
}

#[derive(Debug, Deserialize)]
struct ScopeExclusionsExtraction {
    scope_exclusions: Vec<ExtractedScopeExclusion>,
    no_scope_exclusions_declared: bool,
    detected_inconsistencies: Vec<DetectedInconsistency>,
}

#[derive(Debug, Deserialize)]
struct ExtractedScopeExclusion {
    kind: String,
    text: String,
}

#[derive(Debug, Deserialize)]
struct DetectedInconsistency {
    id: String,
    message: String,
}

pub fn run_scope_exclusions_scope() -> Result<()> {
    let artifact = load_requirements().context("failed to load requirements artifact")?;

    let clarification = find_pending_clarification(&artifact, SCOPE_EXCLUSIONS_CLARIFICATION_ID)?;
    let question = generate_scope_exclusions_question(&artifact, &clarification)?;

    println!("Current question:");
    println!("{question}");
    println!();

    print!("Answer> ");
    io::stdout().flush()?;

    let mut answer = String::new();
    io::stdin().read_line(&mut answer)?;

    let updated_artifact = update_scope_exclusions(artifact, &clarification, answer.trim())?;

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

fn generate_scope_exclusions_question(
    artifact: &RequirementsArtifact,
    clarification: &PendingClarification,
) -> Result<String> {
    let prompt_input = json!({
        "clarification": clarification,
        "current_value": artifact.scope.scope_exclusions,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
            "scope": {
                "capability_categories": artifact.scope.capability_categories,
                "mandatory_constraints": artifact.scope.mandatory_constraints,
            }
        }
    });

    let question_value = llm::call_llm_json(
        QUESTION_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to generate scope-exclusions clarification question")?;

    let generated: ClarificationQuestion = serde_json::from_value(question_value)
        .context("LLM JSON does not match ClarificationQuestion schema")?;

    if generated.question.trim().is_empty() {
        anyhow::bail!("generated scope-exclusions question must not be empty");
    }

    Ok(generated.question)
}

pub fn update_scope_exclusions(
    artifact: RequirementsArtifact,
    clarification: &PendingClarification,
    user_answer: &str,
) -> Result<RequirementsArtifact> {
    validate_requirements_artifact(&artifact)
        .context("invalid requirements artifact before scope-exclusions update")?;

    if user_answer.trim().is_empty() {
        anyhow::bail!("user_answer must not be empty");
    }

    let prompt_input = json!({
        "clarification": clarification,
        "user_answer": user_answer,
        "current_value": artifact.scope.scope_exclusions,
        "relevant_context": {
            "intent": artifact.intent,
            "product": artifact.product,
            "scope": {
                "capability_categories": artifact.scope.capability_categories,
                "mandatory_constraints": artifact.scope.mandatory_constraints,
            }
        }
    });

    let extraction_value = llm::call_llm_json(
        EXTRACT_SYSTEM_PROMPT,
        &serde_json::to_string_pretty(&prompt_input)?,
    )
    .context("failed to extract scope-exclusions")?;

    let extraction: ScopeExclusionsExtraction = serde_json::from_value(extraction_value)
        .context("LLM JSON does not match ScopeExclusionsExtraction schema")?;

    apply_scope_exclusions_extraction(artifact, &extraction)
}

fn apply_scope_exclusions_extraction(
    artifact: RequirementsArtifact,
    extraction: &ScopeExclusionsExtraction,
) -> Result<RequirementsArtifact> {
    validate_scope_exclusions_extraction(extraction)?;

    if extraction.scope_exclusions.is_empty()
        && !extraction.no_scope_exclusions_declared
        && extraction.detected_inconsistencies.is_empty()
    {
        anyhow::bail!("scope-exclusions answer did not clarify scope_exclusions");
    }

    let mut artifact_value = serde_json::to_value(&artifact)
        .context("failed to convert requirements artifact to JSON value")?;

    if !extraction.scope_exclusions.is_empty() {
        let scope_exclusions: Vec<ScopeExclusion> = extraction
            .scope_exclusions
            .iter()
            .map(|item| ScopeExclusion {
                kind: item.kind.clone(),
                text: item.text.clone(),
            })
            .collect();

        set_value_at_path(
            &mut artifact_value,
            &["scope".to_string(), "scope_exclusions".to_string()],
            serde_json::to_value(scope_exclusions)
                .context("failed to serialize scope_exclusions")?,
        )
        .context("failed to set scope.scope_exclusions")?;
    }

    if !extraction.detected_inconsistencies.is_empty() {
        let inconsistencies = artifact_value
            .get_mut("inconsistencies")
            .and_then(Value::as_array_mut)
            .ok_or_else(|| anyhow!("inconsistencies must be an array"))?;

        for detected in &extraction.detected_inconsistencies {
            let built = build_scope_exclusions_inconsistency(detected)?;
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
    .context("failed to set maturity after scope-exclusions update")?;

    if extraction.detected_inconsistencies.is_empty()
        && (!extraction.scope_exclusions.is_empty() || extraction.no_scope_exclusions_declared)
    {
        let _removed = remove_pending_clarification_by_id(
            &mut artifact_value,
            SCOPE_EXCLUSIONS_CLARIFICATION_ID,
        )?;
    }

    let updated_artifact: RequirementsArtifact = serde_json::from_value(artifact_value)
        .context("mutated JSON does not match RequirementsArtifact schema")?;

    validate_requirements_artifact(&updated_artifact)
        .context("scope-exclusions update produced invalid requirements artifact")?;

    validate_scope_exclusions_result(&updated_artifact, extraction)?;

    Ok(updated_artifact)
}

fn validate_scope_exclusions_extraction(extraction: &ScopeExclusionsExtraction) -> Result<()> {
    const ALLOWED_NON_GOAL_KINDS: &[&str] = &["permanent", "release", "deferred"];

    for (index, item) in extraction.scope_exclusions.iter().enumerate() {
        if item.kind.trim().is_empty() {
            anyhow::bail!("scope_exclusions[{index}].kind must not be empty");
        }
        if !ALLOWED_NON_GOAL_KINDS.contains(&item.kind.as_str()) {
            anyhow::bail!(
                "scope_exclusions[{index}].kind must be one of {:?}, got {:?}",
                ALLOWED_NON_GOAL_KINDS,
                item.kind
            );
        }
        if item.text.trim().is_empty() {
            anyhow::bail!("scope_exclusions[{index}].text must not be empty");
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

    if extraction.no_scope_exclusions_declared {
        if !extraction.scope_exclusions.is_empty() {
            anyhow::bail!(
                "no_scope_exclusions_declared=true requires scope_exclusions to be empty"
            );
        }
        if !extraction.detected_inconsistencies.is_empty() {
            anyhow::bail!(
                "no_scope_exclusions_declared=true requires detected_inconsistencies to be empty"
            );
        }
    }

    if !extraction.scope_exclusions.is_empty() && extraction.no_scope_exclusions_declared {
        anyhow::bail!(
            "scope_exclusions non-empty requires no_scope_exclusions_declared=false"
        );
    }

    Ok(())
}

fn build_scope_exclusions_inconsistency(detected: &DetectedInconsistency) -> Result<Inconsistency> {
    if detected.id.trim().is_empty() {
        anyhow::bail!("detected inconsistency id must not be empty");
    }
    if detected.message.trim().is_empty() {
        anyhow::bail!("detected inconsistency message must not be empty");
    }

    Ok(Inconsistency {
        id: format!("scope.scope_exclusions.{}", detected.id),
        stage: "scope".to_string(),
        sieve: SCOPE_EXCLUSIONS_SIEVE_ID.to_string(),
        severity: "blocking".to_string(),
        target_paths: vec![vec!["scope".to_string(), "scope_exclusions".to_string()]],
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

fn validate_scope_exclusions_result(
    artifact: &RequirementsArtifact,
    extraction: &ScopeExclusionsExtraction,
) -> Result<()> {
    if !extraction.scope_exclusions.is_empty() && artifact.scope.scope_exclusions.is_empty() {
        anyhow::bail!("scope-exclusions update must populate scope.scope_exclusions");
    }

    if extraction.no_scope_exclusions_declared && !artifact.scope.scope_exclusions.is_empty() {
        anyhow::bail!(
            "no_scope_exclusions_declared=true requires scope.scope_exclusions to remain empty"
        );
    }

    let has_pending = artifact
        .pending_clarifications
        .iter()
        .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID);

    if extraction.detected_inconsistencies.is_empty()
        && (!extraction.scope_exclusions.is_empty() || extraction.no_scope_exclusions_declared)
        && has_pending
    {
        anyhow::bail!(
            "scope_exclusions pending clarification must be removed after successful update"
        );
    }

    if !extraction.detected_inconsistencies.is_empty() {
        if !has_pending {
            anyhow::bail!(
                "scope_exclusions pending clarification must remain when inconsistencies exist"
            );
        }
        if !artifact
            .inconsistencies
            .iter()
            .any(|item| item.sieve == SCOPE_EXCLUSIONS_SIEVE_ID)
        {
            anyhow::bail!(
                "scope-exclusions inconsistencies must be appended with matching sieve"
            );
        }
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
                raw_input: "做一个校园二手交易平台".to_string(),
                goal: "做一个校园二手交易平台".to_string(),
                domain: "校园二手交易".to_string(),
            },
            product: Product {
                target_users: vec!["大学生".to_string()],
                application_type: vec!["Web 应用".to_string()],
                target_platforms: vec!["Web".to_string()],
            },
            scope: Scope {
                capability_categories: vec!["商品交易".to_string()],
                mandatory_constraints: vec![],
                scope_exclusions: vec![],
            },
            functional_requirements: vec![],
            non_functional_requirements: vec![],
            external_interfaces: vec![],
            data_requirements: vec![],
            pending_clarifications: vec![PendingClarification {
                id: SCOPE_EXCLUSIONS_CLARIFICATION_ID.to_string(),
                target_path: vec!["scope".to_string(), "scope_exclusions".to_string()],
                question: "有没有明确不做的范围？".to_string(),
                sieve: SCOPE_EXCLUSIONS_SIEVE_ID.to_string(),
            }],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn normal_scope_exclusions_accepted() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![
                ExtractedScopeExclusion {
                    kind: "release".to_string(),
                    text: "首版不开发移动端应用".to_string(),
                },
                ExtractedScopeExclusion {
                    kind: "deferred".to_string(),
                    text: "暂不支持跨校交易".to_string(),
                },
            ],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.scope_exclusions[0].kind, "release");
        assert_eq!(updated.scope.scope_exclusions[1].kind, "deferred");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn no_scope_exclusions_declared_is_valid_completion() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: true,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated.scope.scope_exclusions.is_empty());
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        assert!(updated.inconsistencies.is_empty());
    }

    #[test]
    fn uncertain_absence_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "ambiguous_scope_exclusion_commitment".to_string(),
                message: "用户没有说明该范围排除项是永久排除、当前版本排除，还是暂缓考虑，需要进一步澄清。".to_string(),
            }],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        let inconsistency = updated
            .inconsistencies
            .iter()
            .find(|item| item.sieve == SCOPE_EXCLUSIONS_SIEVE_ID)
            .expect("must have inconsistency");
        assert_eq!(inconsistency.severity, "blocking");
    }

    #[test]
    fn functional_requirement_answer_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "functional_requirement_instead_of_scope_exclusion".to_string(),
                message: "用户回答主要描述功能或能力，而不是明确不做或暂不支持的范围。".to_string(),
            }],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == SCOPE_EXCLUSIONS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn explicit_constraint_answer_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "mandatory_constraint_instead_of_scope_exclusion".to_string(),
                message: "用户回答更像必须遵守的禁止性约束，而不是产品范围排除项。".to_string(),
            }],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == SCOPE_EXCLUSIONS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn mixed_valid_non_goal_and_inconsistency_keeps_pending() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "release".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "mandatory_constraint_instead_of_scope_exclusion".to_string(),
                message: "用户回答中包含禁止性约束，应作为 mandatory_constraints 处理，而不是 scope_exclusions。".to_string(),
            }],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.scope_exclusions[0].kind, "release");
        assert_eq!(updated.scope.scope_exclusions[0].text, "不开发移动端应用");
        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == SCOPE_EXCLUSIONS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn permanent_non_goal_accepted() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "permanent".to_string(),
                text: "原则上不支持校外用户交易".to_string(),
            }],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.scope_exclusions[0].kind, "permanent");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
    }

    #[test]
    fn deferred_non_goal_accepted() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "deferred".to_string(),
                text: "暂时不开发移动端应用，后续再考虑".to_string(),
            }],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert_eq!(updated.scope.scope_exclusions[0].kind, "deferred");
        assert!(!updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
    }

    #[test]
    fn invalid_kind_rejected() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "temporary".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_scope_exclusions_extraction(artifact, &extraction)
            .expect_err("invalid kind should fail");
        assert!(err.to_string().contains("scope_exclusions[0].kind must be one of"));
    }

    #[test]
    fn empty_kind_rejected() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_scope_exclusions_extraction(artifact, &extraction)
            .expect_err("empty kind should fail");
        assert!(err.to_string().contains("scope_exclusions[0].kind must not be empty"));
    }

    #[test]
    fn empty_text_rejected() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "release".to_string(),
                text: "".to_string(),
            }],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_scope_exclusions_extraction(artifact, &extraction)
            .expect_err("empty text should fail");
        assert!(err.to_string().contains("scope_exclusions[0].text must not be empty"));
    }

    #[test]
    fn ambiguous_commitment_produces_blocking_inconsistency() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "ambiguous_scope_exclusion_commitment".to_string(),
                message: "用户没有说明该范围排除项是永久排除、当前版本排除，还是暂缓考虑，需要进一步澄清。".to_string(),
            }],
        };

        let updated =
            apply_scope_exclusions_extraction(artifact, &extraction).expect("update should succeed");

        assert!(updated
            .pending_clarifications
            .iter()
            .any(|item| item.id == SCOPE_EXCLUSIONS_CLARIFICATION_ID));
        assert!(updated
            .inconsistencies
            .iter()
            .any(|item| item.sieve == SCOPE_EXCLUSIONS_SIEVE_ID && item.severity == "blocking"));
    }

    #[test]
    fn no_declared_true_with_non_empty_scope_exclusions_rejected() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![ExtractedScopeExclusion {
                kind: "release".to_string(),
                text: "不开发移动端应用".to_string(),
            }],
            no_scope_exclusions_declared: true,
            detected_inconsistencies: vec![],
        };

        let err = apply_scope_exclusions_extraction(artifact, &extraction)
            .expect_err("invalid extraction should fail");
        assert!(err
            .to_string()
            .contains("no_scope_exclusions_declared=true requires scope_exclusions to be empty"));
    }

    #[test]
    fn no_declared_true_with_inconsistencies_rejected() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: true,
            detected_inconsistencies: vec![DetectedInconsistency {
                id: "vague_non_goal".to_string(),
                message: "用户回答过于宽泛，无法形成可执行的范围排除项边界。".to_string(),
            }],
        };

        let err = apply_scope_exclusions_extraction(artifact, &extraction)
            .expect_err("invalid extraction should fail");
        assert!(err.to_string().contains(
            "no_scope_exclusions_declared=true requires detected_inconsistencies to be empty"
        ));
    }

    #[test]
    fn empty_extraction_rejected() {
        let artifact = base_artifact();
        let extraction = ScopeExclusionsExtraction {
            scope_exclusions: vec![],
            no_scope_exclusions_declared: false,
            detected_inconsistencies: vec![],
        };

        let err = apply_scope_exclusions_extraction(artifact, &extraction)
            .expect_err("empty extraction should fail");
        assert!(err
            .to_string()
            .contains("scope-exclusions answer did not clarify scope_exclusions"));
    }
}
