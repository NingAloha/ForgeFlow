use anyhow::{bail, Result};

use crate::sieves::requirements::artifact::{
    Constraint,
    Inconsistency,
    PendingClarification,
    RequirementsArtifact,
    ALLOWED_MATURITY,
    EXPECTED_ARTIFACT_TYPE,
    EXPECTED_SCHEMA_VERSION,
};

pub fn validate_requirements_artifact(artifact: &RequirementsArtifact) -> Result<()> {
    if artifact.artifact_type != EXPECTED_ARTIFACT_TYPE {
        bail!(
            "requirements artifact.artifact_type must be {:?}, got {:?}",
            EXPECTED_ARTIFACT_TYPE,
            artifact.artifact_type
        );
    }

    if artifact.schema_version != EXPECTED_SCHEMA_VERSION {
        bail!(
            "requirements artifact.schema_version must be {:?}, got {:?}",
            EXPECTED_SCHEMA_VERSION,
            artifact.schema_version
        );
    }

    if !ALLOWED_MATURITY.contains(&artifact.maturity.as_str()) {
        bail!(
            "requirements artifact.maturity must be one of {:?}, got {:?}",
            ALLOWED_MATURITY,
            artifact.maturity
        );
    }

    validate_string_list(
        &artifact.product.target_users,
        "requirements artifact.product.target_users",
    )?;
    validate_string_list(
        &artifact.product.application_type,
        "requirements artifact.product.application_type",
    )?;
    validate_string_list(
        &artifact.product.target_platforms,
        "requirements artifact.product.target_platforms",
    )?;

    validate_string_list(
        &artifact.scope.capability_categories,
        "requirements artifact.scope.capability_categories",
    )?;
    validate_explicit_constraints(
        &artifact.scope.explicit_constraints,
        "requirements artifact.scope.explicit_constraints",
    )?;
    validate_string_list(
        &artifact.scope.non_goals,
        "requirements artifact.scope.non_goals",
    )?;

    validate_pending_clarifications(
        &artifact.pending_clarifications,
        "requirements artifact.pending_clarifications",
    )?;
    validate_inconsistencies(
        &artifact.inconsistencies,
        "requirements artifact.inconsistencies",
    )?;

    Ok(())
}

fn validate_string_list(values: &[String], field_path: &str) -> Result<()> {
    for (index, value) in values.iter().enumerate() {
        if value.trim().is_empty() {
            bail!("{field_path}[{index}] must not be empty");
        }
    }

    Ok(())
}

fn validate_pending_clarifications(
    values: &[PendingClarification],
    field_path: &str,
) -> Result<()> {
    for (index, value) in values.iter().enumerate() {
        if value.id.trim().is_empty() {
            bail!("{field_path}[{index}].id must not be empty");
        }
        if value.target_path.is_empty() {
            bail!("{field_path}[{index}].target_path must not be empty");
        }
        if value.question.trim().is_empty() {
            bail!("{field_path}[{index}].question must not be empty");
        }
        if value.sieve.trim().is_empty() {
            bail!("{field_path}[{index}].sieve must not be empty");
        }

        let expected_id = value.target_path.join(".");
        if value.id != expected_id {
            bail!(
                "{field_path}[{index}].id must equal target_path joined by '.', expected {:?}, got {:?}",
                expected_id,
                value.id
            );
        }
    }

    Ok(())
}

fn validate_explicit_constraints(values: &[Constraint], field_path: &str) -> Result<()> {
    const ALLOWED_CONSTRAINT_KINDS: &[&str] = &[
        "technical",
        "platform",
        "policy",
        "resource",
        "performance",
        "integration",
        "data",
        "business",
        "scope",
        "other",
    ];

    for (index, value) in values.iter().enumerate() {
        if value.kind.trim().is_empty() {
            bail!("{field_path}[{index}].kind must not be empty");
        }
        if !ALLOWED_CONSTRAINT_KINDS.contains(&value.kind.as_str()) {
            bail!(
                "{field_path}[{index}].kind must be one of {:?}, got {:?}",
                ALLOWED_CONSTRAINT_KINDS,
                value.kind
            );
        }
        if value.text.trim().is_empty() {
            bail!("{field_path}[{index}].text must not be empty");
        }
    }

    Ok(())
}

fn validate_inconsistencies(
    values: &[Inconsistency],
    field_path: &str,
) -> Result<()> {
    for (index, value) in values.iter().enumerate() {
        if value.id.trim().is_empty() {
            bail!("{field_path}[{index}].id must not be empty");
        }
        if value.stage.trim().is_empty() {
            bail!("{field_path}[{index}].stage must not be empty");
        }
        if value.sieve.trim().is_empty() {
            bail!("{field_path}[{index}].sieve must not be empty");
        }
        if value.severity.trim().is_empty() {
            bail!("{field_path}[{index}].severity must not be empty");
        }
        if value.severity != "blocking" && value.severity != "warning" {
            bail!(
                "{field_path}[{index}].severity must be \"blocking\" or \"warning\", got {:?}",
                value.severity
            );
        }
        if value.target_paths.is_empty() {
            bail!("{field_path}[{index}].target_paths must not be empty");
        }
        for (path_index, path) in value.target_paths.iter().enumerate() {
            if path.is_empty() {
                bail!(
                    "{field_path}[{index}].target_paths[{path_index}] must not be empty"
                );
            }
            for (segment_index, segment) in path.iter().enumerate() {
                if segment.trim().is_empty() {
                    bail!(
                        "{field_path}[{index}].target_paths[{path_index}][{segment_index}] must not be empty"
                    );
                }
            }
        }
        if value.message.trim().is_empty() {
            bail!("{field_path}[{index}].message must not be empty");
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::sieves::requirements::artifact::{
        Constraint,
        Inconsistency,
        Intent,
        Product,
        RequirementsArtifact,
        Scope,
    };

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
                target_users: vec![],
                application_type: vec![],
                target_platforms: vec![],
            },
            scope: Scope {
                capability_categories: vec![],
                explicit_constraints: vec![],
                non_goals: vec![],
            },
            functional_requirements: vec![],
            non_functional_requirements: vec![],
            external_interfaces: vec![],
            data_requirements: vec![],
            pending_clarifications: vec![],
            inconsistencies: vec![],
        }
    }

    #[test]
    fn allows_empty_inconsistencies() {
        let artifact = base_artifact();
        validate_requirements_artifact(&artifact)
            .expect("empty inconsistencies should be valid");
    }

    #[test]
    fn allows_empty_explicit_constraints() {
        let artifact = base_artifact();
        validate_requirements_artifact(&artifact)
            .expect("empty explicit_constraints should be valid");
    }

    #[test]
    fn allows_valid_structured_constraint() {
        let mut artifact = base_artifact();
        artifact.scope.explicit_constraints.push(Constraint {
            kind: "technical".to_string(),
            text: "必须使用 PostgreSQL".to_string(),
        });

        validate_requirements_artifact(&artifact)
            .expect("valid structured constraint should pass");
    }

    #[test]
    fn allows_multiple_valid_constraint_kinds() {
        let mut artifact = base_artifact();
        artifact.scope.explicit_constraints = vec![
            Constraint {
                kind: "technical".to_string(),
                text: "必须使用 PostgreSQL".to_string(),
            },
            Constraint {
                kind: "policy".to_string(),
                text: "必须使用校内邮箱认证".to_string(),
            },
            Constraint {
                kind: "resource".to_string(),
                text: "首版由一人维护".to_string(),
            },
            Constraint {
                kind: "scope".to_string(),
                text: "首版只服务本校用户".to_string(),
            },
        ];

        validate_requirements_artifact(&artifact)
            .expect("multiple valid explicit_constraints should pass");
    }

    #[test]
    fn rejects_invalid_constraint_kind() {
        let mut artifact = base_artifact();
        artifact.scope.explicit_constraints.push(Constraint {
            kind: "random".to_string(),
            text: "xxx".to_string(),
        });

        let err = validate_requirements_artifact(&artifact)
            .expect_err("invalid constraint kind should fail");
        assert!(err.to_string().contains(".kind must be one of"));
    }

    #[test]
    fn rejects_empty_constraint_kind() {
        let mut artifact = base_artifact();
        artifact.scope.explicit_constraints.push(Constraint {
            kind: "".to_string(),
            text: "必须使用 PostgreSQL".to_string(),
        });

        let err = validate_requirements_artifact(&artifact)
            .expect_err("empty constraint kind should fail");
        assert!(err.to_string().contains(".kind must not be empty"));
    }

    #[test]
    fn rejects_empty_constraint_text() {
        let mut artifact = base_artifact();
        artifact.scope.explicit_constraints.push(Constraint {
            kind: "technical".to_string(),
            text: "".to_string(),
        });

        let err = validate_requirements_artifact(&artifact)
            .expect_err("empty constraint text should fail");
        assert!(err.to_string().contains(".text must not be empty"));
    }

    #[test]
    fn allows_valid_structured_inconsistency() {
        let mut artifact = base_artifact();
        artifact.inconsistencies.push(Inconsistency {
            id: "scope.application_boundary.cli_mobile_platform_conflict".to_string(),
            stage: "scope".to_string(),
            sieve: "requirements.scope.application_boundary".to_string(),
            severity: "blocking".to_string(),
            target_paths: vec![
                vec!["product".to_string(), "application_type".to_string()],
                vec!["product".to_string(), "target_platforms".to_string()],
            ],
            message: "CLI 工具通常不以 iOS/Android 作为直接运行平台，需要进一步澄清目标运行环境。".to_string(),
            requires_clarification: true,
        });

        validate_requirements_artifact(&artifact)
            .expect("valid structured inconsistency should pass");
    }

    #[test]
    fn rejects_invalid_severity() {
        let mut artifact = base_artifact();
        artifact.inconsistencies.push(Inconsistency {
            id: "scope.application_boundary.cli_mobile_platform_conflict".to_string(),
            stage: "scope".to_string(),
            sieve: "requirements.scope.application_boundary".to_string(),
            severity: "critical".to_string(),
            target_paths: vec![vec![
                "product".to_string(),
                "application_type".to_string(),
            ]],
            message: "x".to_string(),
            requires_clarification: true,
        });

        let err = validate_requirements_artifact(&artifact)
            .expect_err("invalid severity should fail");
        assert!(err.to_string().contains("severity must be \"blocking\" or \"warning\""));
    }

    #[test]
    fn rejects_empty_target_paths() {
        let mut artifact = base_artifact();
        artifact.inconsistencies.push(Inconsistency {
            id: "scope.application_boundary.cli_mobile_platform_conflict".to_string(),
            stage: "scope".to_string(),
            sieve: "requirements.scope.application_boundary".to_string(),
            severity: "blocking".to_string(),
            target_paths: vec![],
            message: "x".to_string(),
            requires_clarification: true,
        });

        let err = validate_requirements_artifact(&artifact)
            .expect_err("empty target_paths should fail");
        assert!(err.to_string().contains("target_paths must not be empty"));
    }

    #[test]
    fn rejects_empty_id_or_message() {
        let mut artifact = base_artifact();
        artifact.inconsistencies.push(Inconsistency {
            id: "".to_string(),
            stage: "scope".to_string(),
            sieve: "requirements.scope.application_boundary".to_string(),
            severity: "warning".to_string(),
            target_paths: vec![vec![
                "product".to_string(),
                "target_platforms".to_string(),
            ]],
            message: "".to_string(),
            requires_clarification: false,
        });

        let err = validate_requirements_artifact(&artifact)
            .expect_err("empty id/message should fail");
        assert!(err.to_string().contains(".id must not be empty"));
    }
}
