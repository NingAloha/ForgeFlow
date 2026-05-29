use anyhow::{Result, anyhow};
use serde_json::Value;

use crate::llm::call_llm_json;

pub fn capture_core_approach_from_context(context: &Value) -> Result<Value> {
    let user_prompt = serde_json::to_string_pretty(context)
        .map_err(|err| anyhow!("failed to serialize core_approach capture context: {err}"))?;

    let response = call_llm_json(
        include_str!("prompts/core_approach_capture_system.txt"),
        &user_prompt,
    )?;

    validate_core_approach_capture_response(response)
}

fn validate_core_approach_capture_response(response: Value) -> Result<Value> {
    let top = response
        .as_object()
        .ok_or_else(|| anyhow!("core_approach capture response must be a JSON object"))?;

    if top.len() != 1 || !top.contains_key("boundary") {
        return Err(anyhow!(
            "core_approach capture response top-level fields must be exactly: boundary"
        ));
    }

    let boundary = top
        .get("boundary")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("boundary must be an object"))?;

    if boundary.len() != 1 || !boundary.contains_key("core_approach") {
        return Err(anyhow!(
            "core_approach capture response boundary fields must be exactly: core_approach"
        ));
    }

    boundary
        .get("core_approach")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("boundary.core_approach must be a string"))?;

    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::validate_core_approach_capture_response;
    use serde_json::json;

    #[test]
    fn validate_core_approach_capture_response_accepts_valid_core_approach() {
        let response = json!({
            "boundary": {
                "core_approach": "通过统一内容空间组织和关联分散信息"
            }
        });

        let validated = validate_core_approach_capture_response(response.clone())
            .expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_core_approach_capture_response_accepts_empty_core_approach() {
        let response = json!({
            "boundary": {
                "core_approach": ""
            }
        });

        let validated = validate_core_approach_capture_response(response.clone())
            .expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_core_approach_capture_response_rejects_missing_core_approach() {
        let response = json!({
            "boundary": {}
        });

        let err = validate_core_approach_capture_response(response).expect_err("expected error");
        assert!(err.to_string().contains(
            "core_approach capture response boundary fields must be exactly: core_approach"
        ));
    }

    #[test]
    fn validate_core_approach_capture_response_rejects_extra_top_level_field() {
        let response = json!({
            "boundary": {
                "core_approach": "通过版本控制和 Pull Request 组织代码协作"
            },
            "extra": {}
        });

        let err = validate_core_approach_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string().contains(
                "core_approach capture response top-level fields must be exactly: boundary"
            )
        );
    }

    #[test]
    fn validate_core_approach_capture_response_rejects_extra_boundary_field() {
        let response = json!({
            "boundary": {
                "core_approach": "通过命令行 Agent 理解项目上下文并协助修改代码",
                "extra": "x"
            }
        });

        let err = validate_core_approach_capture_response(response).expect_err("expected error");
        assert!(err.to_string().contains(
            "core_approach capture response boundary fields must be exactly: core_approach"
        ));
    }
}
