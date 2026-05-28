use anyhow::{bail, Result};

use crate::sieves::requirements::artifact::{
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
    validate_string_list(
        &artifact.scope.constraints,
        "requirements artifact.scope.constraints",
    )?;
    validate_string_list(
        &artifact.scope.non_goals,
        "requirements artifact.scope.non_goals",
    )?;

    validate_pending_clarifications(
        &artifact.pending_clarifications,
        "requirements artifact.pending_clarifications",
    )?;
    validate_string_list(
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
