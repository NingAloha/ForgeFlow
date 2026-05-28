use anyhow::{Context, Result};
use serde_json::Value;
use std::fs;
use std::path::Path;

use crate::runtime::paths::{
    REQUIREMENTS_EXAMPLE_PATH,
    REQUIREMENTS_RUNTIME_PATH,
};
use crate::sieves::requirements::artifact::RequirementsArtifact;
use crate::sieves::requirements::validator::validate_requirements_artifact;

pub fn load_requirements_example_as_value() -> Result<Value> {
    load_json_value_from_path(REQUIREMENTS_EXAMPLE_PATH)
        .context("failed to load requirements example as JSON value")
}

pub fn load_requirements() -> Result<RequirementsArtifact> {
    let raw = fs::read_to_string(REQUIREMENTS_RUNTIME_PATH)
        .with_context(|| {
            format!(
                "failed to read requirements runtime artifact: {}",
                REQUIREMENTS_RUNTIME_PATH
            )
        })?;

    let artifact: RequirementsArtifact = serde_json::from_str(&raw)
        .with_context(|| {
            format!(
                "failed to parse requirements runtime artifact: {}",
                REQUIREMENTS_RUNTIME_PATH
            )
        })?;

    validate_requirements_artifact(&artifact)
        .with_context(|| {
            format!(
                "invalid requirements runtime artifact: {}",
                REQUIREMENTS_RUNTIME_PATH
            )
        })?;

    Ok(artifact)
}

pub fn save_requirements(artifact: &RequirementsArtifact) -> Result<()> {
    validate_requirements_artifact(artifact)
        .context("invalid requirements artifact before save")?;

    let path = Path::new(REQUIREMENTS_RUNTIME_PATH);

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| {
                format!(
                    "failed to create requirements runtime directory: {}",
                    parent.display()
                )
            })?;
    }

    let serialized = serde_json::to_string_pretty(artifact)
        .context("failed to serialize requirements artifact")?;

    fs::write(path, serialized + "\n")
        .with_context(|| {
            format!(
                "failed to write requirements runtime artifact: {}",
                path.display()
            )
        })?;

    Ok(())
}

fn load_json_value_from_path(path: impl AsRef<Path>) -> Result<Value> {
    let path = path.as_ref();

    let raw = fs::read_to_string(path)
        .with_context(|| format!("failed to read JSON file: {}", path.display()))?;

    let value: Value = serde_json::from_str(&raw)
        .with_context(|| format!("failed to parse JSON file: {}", path.display()))?;

    Ok(value)
}