use anyhow::{anyhow, Result};
use serde_json::Value;

pub fn path_to_string(path: &[String]) -> String {
    if path.is_empty() {
        return "<root>".to_string();
    }

    path.join(".")
}

pub fn get_value_at_path<'a>(
    root: &'a Value,
    path: &[String],
) -> Result<&'a Value> {
    if path.is_empty() {
        return Ok(root);
    }

    let mut current = root;

    for segment in path {
        let object = current.as_object().ok_or_else(|| {
            anyhow!(
                "cannot read path {}; segment {:?} requires object, got {}",
                path_to_string(path),
                segment,
                value_type_name(current),
            )
        })?;

        current = object.get(segment).ok_or_else(|| {
            anyhow!(
                "cannot read path {}; segment {:?} does not exist",
                path_to_string(path),
                segment,
            )
        })?;
    }

    Ok(current)
}

fn value_type_name(value: &Value) -> &'static str {
    match value {
        Value::Null => "null",
        Value::Bool(_) => "bool",
        Value::Number(_) => "number",
        Value::String(_) => "string",
        Value::Array(_) => "array",
        Value::Object(_) => "object",
    }
}