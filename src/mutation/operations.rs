use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::mutation::json_read::path_to_string;
use crate::mutation::json_write::{
    remove_string_from_list_at_path,
    set_value_at_path,
};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "op", rename_all = "snake_case")]
pub enum ArtifactOperation {
    Set {
        path: Vec<String>,
        value: Value,
    },
    RemoveFromList {
        path: Vec<String>,
        value: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OperationSet {
    pub operations: Vec<ArtifactOperation>,
}

pub fn apply_operations(
    root: &mut Value,
    operation_set: &OperationSet,
    allowed_paths: &[&[&str]],
) -> Result<()> {
    validate_operation_paths(operation_set, allowed_paths)?;

    for operation in &operation_set.operations {
        apply_operation(root, operation)?;
    }

    Ok(())
}

pub fn validate_operation_paths(
    operation_set: &OperationSet,
    allowed_paths: &[&[&str]],
) -> Result<()> {
    for operation in &operation_set.operations {
        let path = operation_path(operation);

        if path.is_empty() {
            bail!("operation path must not be empty");
        }

        if !is_path_allowed(path, allowed_paths) {
            bail!(
                "operation path {} is not allowed",
                path_to_string(path)
            );
        }
    }

    Ok(())
}

pub fn is_path_allowed(
    path: &[String],
    allowed_paths: &[&[&str]],
) -> bool {
    allowed_paths.iter().any(|allowed_path| {
        if path.len() < allowed_path.len() {
            return false;
        }

        path.iter()
            .zip(allowed_path.iter())
            .all(|(actual, allowed)| actual == allowed)
    })
}

pub fn operation_path(operation: &ArtifactOperation) -> &[String] {
    match operation {
        ArtifactOperation::Set { path, .. } => path,
        ArtifactOperation::RemoveFromList { path, .. } => path,
    }
}

fn apply_operation(
    root: &mut Value,
    operation: &ArtifactOperation,
) -> Result<()> {
    match operation {
        ArtifactOperation::Set { path, value } => {
            set_value_at_path(root, path, value.clone())
        }
        ArtifactOperation::RemoveFromList { path, value } => {
            remove_string_from_list_at_path(root, path, value)
        }
    }
}