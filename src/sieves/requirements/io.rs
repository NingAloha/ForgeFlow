use anyhow::{Context, Result, anyhow};
use serde_json::{Value, json};
use std::fs;
use std::path::Path;

use crate::runtime::paths::{REQUIREMENTS_EXAMPLE_PATH, REQUIREMENTS_RUNTIME_PATH};

pub fn write_requirements_capture_output(capture_output: &Value) -> Result<()> {
    let mut runtime = load_runtime_or_example_json()?;
    apply_capture_output(&mut runtime, capture_output)?;
    write_runtime_json(&runtime)
}

pub fn read_requirements_context_slice(paths: &[&str]) -> Result<Value> {
    let runtime = read_runtime_json()?;
    build_context_slice_from_runtime(&runtime, paths)
}

fn load_runtime_or_example_json() -> Result<Value> {
    let runtime_path = Path::new(REQUIREMENTS_RUNTIME_PATH);
    let source_path = if runtime_path.exists() {
        REQUIREMENTS_RUNTIME_PATH
    } else {
        REQUIREMENTS_EXAMPLE_PATH
    };

    let content = fs::read_to_string(source_path)
        .with_context(|| format!("failed to read JSON file: {source_path}"))?;
    let value: Value = serde_json::from_str(&content)
        .with_context(|| format!("failed to parse JSON file: {source_path}"))?;

    if !value.is_object() {
        return Err(anyhow!("requirements runtime JSON must be an object"));
    }

    Ok(value)
}

fn write_runtime_json(value: &Value) -> Result<()> {
    if !value.is_object() {
        return Err(anyhow!("requirements runtime JSON must be an object"));
    }

    let runtime_path = Path::new(REQUIREMENTS_RUNTIME_PATH);
    if let Some(parent) = runtime_path.parent() {
        fs::create_dir_all(parent)
            .with_context(|| format!("failed to create directory: {}", parent.display()))?;
    }

    let mut content = serde_json::to_string_pretty(value)
        .context("failed to serialize requirements runtime JSON")?;
    content.push('\n');

    fs::write(runtime_path, content)
        .with_context(|| format!("failed to write JSON file: {}", runtime_path.display()))?;

    Ok(())
}

fn read_runtime_json() -> Result<Value> {
    let content = fs::read_to_string(REQUIREMENTS_RUNTIME_PATH)
        .with_context(|| format!("failed to read JSON file: {REQUIREMENTS_RUNTIME_PATH}"))?;
    let value: Value = serde_json::from_str(&content)
        .with_context(|| format!("failed to parse JSON file: {REQUIREMENTS_RUNTIME_PATH}"))?;
    if !value.is_object() {
        return Err(anyhow!("requirements runtime JSON must be an object"));
    }
    Ok(value)
}

fn build_context_slice_from_runtime(runtime: &Value, paths: &[&str]) -> Result<Value> {
    if paths.is_empty() {
        return Err(anyhow!("context slice paths must not be empty"));
    }

    let mut slice = json!({});
    for raw_path in paths {
        let path = raw_path.trim();
        if path.is_empty() {
            return Err(anyhow!("context slice path must not be empty"));
        }

        let value = get_value_by_dot_path(runtime, path)?;
        insert_value_by_dot_path(&mut slice, path, value.clone())?;
    }

    Ok(slice)
}

fn get_value_by_dot_path<'a>(root: &'a Value, path: &str) -> Result<&'a Value> {
    let mut current = root;
    let parts: Vec<&str> = path.split('.').collect();
    for (idx, key) in parts.iter().enumerate() {
        if key.is_empty() {
            return Err(anyhow!("context slice path must not be empty"));
        }

        let obj = current
            .as_object()
            .ok_or_else(|| anyhow!("context slice path is not traversable: {path}"))?;
        let next = obj
            .get(*key)
            .ok_or_else(|| anyhow!("missing context slice path: {path}"))?;

        if idx + 1 < parts.len() && !next.is_object() {
            return Err(anyhow!("context slice path is not traversable: {path}"));
        }
        current = next;
    }
    Ok(current)
}

fn insert_value_by_dot_path(target: &mut Value, path: &str, value: Value) -> Result<()> {
    let parts: Vec<&str> = path.split('.').collect();
    if parts.is_empty() {
        return Err(anyhow!("context slice path must not be empty"));
    }

    let mut current = target;
    for (idx, key) in parts.iter().enumerate() {
        if key.is_empty() {
            return Err(anyhow!("context slice path must not be empty"));
        }

        let is_last = idx + 1 == parts.len();
        let obj = current
            .as_object_mut()
            .ok_or_else(|| anyhow!("context slice path is not traversable: {path}"))?;

        if is_last {
            obj.insert((*key).to_string(), value.clone());
            return Ok(());
        }

        let entry = obj.entry((*key).to_string()).or_insert_with(|| json!({}));
        if !entry.is_object() {
            return Err(anyhow!("context slice path is not traversable: {path}"));
        }
        current = entry;
    }

    Ok(())
}

fn apply_capture_output(runtime: &mut Value, capture_output: &Value) -> Result<()> {
    let capture_obj = capture_output
        .as_object()
        .ok_or_else(|| anyhow!("capture_output must be a JSON object"))?;

    if capture_obj.is_empty() {
        return Err(anyhow!("capture_output must not be empty"));
    }

    if capture_obj.len() != 2
        || !capture_obj.contains_key("origin")
        || !capture_obj.contains_key("boundary")
    {
        return Err(anyhow!(
            "capture_output top-level fields must be exactly: origin, boundary"
        ));
    }

    let origin = capture_obj
        .get("origin")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("capture_output.origin must be an object"))?;
    if origin.len() != 1 || !origin.contains_key("raw_input") {
        return Err(anyhow!(
            "capture_output.origin fields must be exactly: raw_input"
        ));
    }

    let raw_input = origin
        .get("raw_input")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("capture_output.origin.raw_input must be a string"))?;

    let boundary = capture_obj
        .get("boundary")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("capture_output.boundary must be an object"))?;
    if boundary.len() != 1 || !boundary.contains_key("domain") {
        return Err(anyhow!(
            "capture_output.boundary fields must be exactly: domain"
        ));
    }

    let domain = boundary
        .get("domain")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("capture_output.boundary.domain must be a string"))?;

    let runtime_obj = runtime
        .as_object_mut()
        .ok_or_else(|| anyhow!("requirements runtime JSON must be an object"))?;

    let runtime_origin = runtime_obj
        .entry("origin")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or_else(|| anyhow!("runtime origin must be an object"))?;
    runtime_origin.insert(
        "raw_input".to_string(),
        Value::String(raw_input.to_string()),
    );

    let runtime_boundary = runtime_obj
        .entry("boundary")
        .or_insert_with(|| json!({}))
        .as_object_mut()
        .ok_or_else(|| anyhow!("runtime boundary must be an object"))?;
    runtime_boundary.insert("domain".to_string(), Value::String(domain.to_string()));

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        apply_capture_output, build_context_slice_from_runtime, get_value_by_dot_path,
        insert_value_by_dot_path,
    };
    use serde_json::json;

    #[test]
    fn apply_capture_output_updates_origin_and_boundary() {
        let mut runtime = json!({
            "artifact_type": "requirements",
            "schema_version": "0.1",
            "origin": { "raw_input": "old" },
            "boundary": { "domain": "old-domain" }
        });
        let capture_output = json!({
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "软件开发工具" }
        });

        apply_capture_output(&mut runtime, &capture_output).expect("should succeed");

        assert_eq!(runtime["origin"]["raw_input"], "做一个 IDE");
        assert_eq!(runtime["boundary"]["domain"], "软件开发工具");
    }

    #[test]
    fn apply_capture_output_allows_empty_boundary_domain() {
        let mut runtime = json!({
            "artifact_type": "requirements",
            "schema_version": "0.1",
            "origin": { "raw_input": "old" },
            "boundary": { "domain": "old-domain" }
        });
        let capture_output = json!({
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "" }
        });

        apply_capture_output(&mut runtime, &capture_output).expect("should succeed");

        assert_eq!(runtime["boundary"]["domain"], "");
    }

    #[test]
    fn apply_capture_output_rejects_extra_top_level_field() {
        let mut runtime = json!({"origin": {}, "boundary": {}});
        let capture_output = json!({
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "软件开发工具" },
            "extra": {}
        });

        let err = apply_capture_output(&mut runtime, &capture_output).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("capture_output top-level fields must be exactly: origin, boundary")
        );
    }

    #[test]
    fn apply_capture_output_rejects_extra_origin_field() {
        let mut runtime = json!({"origin": {}, "boundary": {}});
        let capture_output = json!({
            "origin": { "raw_input": "做一个 IDE", "extra": "x" },
            "boundary": { "domain": "软件开发工具" }
        });

        let err = apply_capture_output(&mut runtime, &capture_output).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("capture_output.origin fields must be exactly: raw_input")
        );
    }

    #[test]
    fn apply_capture_output_rejects_extra_boundary_field() {
        let mut runtime = json!({"origin": {}, "boundary": {}});
        let capture_output = json!({
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "软件开发工具", "extra": "x" }
        });

        let err = apply_capture_output(&mut runtime, &capture_output).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("capture_output.boundary fields must be exactly: domain")
        );
    }

    #[test]
    fn apply_capture_output_rejects_missing_origin_raw_input() {
        let mut runtime = json!({"origin": {}, "boundary": {}});
        let capture_output = json!({
            "origin": {},
            "boundary": { "domain": "软件开发工具" }
        });

        let err = apply_capture_output(&mut runtime, &capture_output).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("capture_output.origin fields must be exactly: raw_input")
        );
    }

    #[test]
    fn apply_capture_output_rejects_missing_boundary_domain() {
        let mut runtime = json!({"origin": {}, "boundary": {}});
        let capture_output = json!({
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": {}
        });

        let err = apply_capture_output(&mut runtime, &capture_output).expect_err("should fail");
        assert!(
            err.to_string()
                .contains("capture_output.boundary fields must be exactly: domain")
        );
    }

    #[test]
    fn context_slice_extracts_single_top_level_field() {
        let runtime = json!({
            "artifact_type": "requirements",
            "schema_version": "0.1",
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "软件开发工具" }
        });
        let slice =
            build_context_slice_from_runtime(&runtime, &["artifact_type"]).expect("should build");
        assert_eq!(slice, json!({ "artifact_type": "requirements" }));
    }

    #[test]
    fn context_slice_extracts_nested_field() {
        let runtime = json!({
            "origin": { "raw_input": "做一个 IDE" }
        });
        let slice = build_context_slice_from_runtime(&runtime, &["origin.raw_input"])
            .expect("should build");
        assert_eq!(slice, json!({ "origin": { "raw_input": "做一个 IDE" } }));
    }

    #[test]
    fn context_slice_extracts_multiple_shared_prefix_fields() {
        let runtime = json!({
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "软件开发工具" }
        });
        let slice =
            build_context_slice_from_runtime(&runtime, &["origin.raw_input", "boundary.domain"])
                .expect("should build");
        assert_eq!(
            slice,
            json!({
                "origin": { "raw_input": "做一个 IDE" },
                "boundary": { "domain": "软件开发工具" }
            })
        );
    }

    #[test]
    fn context_slice_rejects_empty_paths() {
        let runtime = json!({ "origin": { "raw_input": "x" } });
        let err = build_context_slice_from_runtime(&runtime, &[]).expect_err("should fail");
        assert_eq!(err.to_string(), "context slice paths must not be empty");
    }

    #[test]
    fn context_slice_rejects_empty_path() {
        let runtime = json!({ "origin": { "raw_input": "x" } });
        let err = build_context_slice_from_runtime(&runtime, &[" "]).expect_err("should fail");
        assert_eq!(err.to_string(), "context slice path must not be empty");
    }

    #[test]
    fn context_slice_rejects_missing_path() {
        let runtime = json!({ "boundary": { "domain": "软件开发工具" } });
        let err = get_value_by_dot_path(&runtime, "boundary.problem").expect_err("should fail");
        assert_eq!(
            err.to_string(),
            "missing context slice path: boundary.problem"
        );
    }

    #[test]
    fn context_slice_rejects_non_traversable_path() {
        let runtime = json!({ "origin": { "raw_input": "做一个 IDE" } });
        let err =
            get_value_by_dot_path(&runtime, "origin.raw_input.text").expect_err("should fail");
        assert_eq!(
            err.to_string(),
            "context slice path is not traversable: origin.raw_input.text"
        );
    }

    #[test]
    fn context_slice_preserves_nested_structure() {
        let runtime = json!({
            "artifact_type": "requirements",
            "origin": { "raw_input": "做一个 IDE" },
            "boundary": { "domain": "软件开发工具" }
        });
        let slice =
            build_context_slice_from_runtime(&runtime, &["origin.raw_input", "boundary.domain"])
                .expect("should build");
        assert_eq!(
            slice,
            json!({
                "origin": { "raw_input": "做一个 IDE" },
                "boundary": { "domain": "软件开发工具" }
            })
        );
    }
}
