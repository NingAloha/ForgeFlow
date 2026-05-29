use anyhow::{Result, anyhow};
use serde_json::Value;

use crate::llm::call_llm_json;
use crate::sieves::requirements::io::read_requirements_context_slice;

pub fn capture_problem_from_context(context: &Value) -> Result<Value> {
    let user_prompt = serde_json::to_string_pretty(context)
        .map_err(|err| anyhow!("failed to serialize problem capture context: {err}"))?;

    let response = call_llm_json(
        include_str!("prompts/problem_capture_system.txt"),
        &user_prompt,
    )?;

    validate_problem_capture_response(response)
}

pub fn capture_problem() -> Result<Value> {
    let context = read_requirements_context_slice(&["origin.raw_input", "boundary.domain"])?;
    capture_problem_from_context(&context)
}

fn validate_problem_capture_response(response: Value) -> Result<Value> {
    let top = response
        .as_object()
        .ok_or_else(|| anyhow!("problem capture response must be a JSON object"))?;

    if top.len() != 1 || !top.contains_key("boundary") {
        return Err(anyhow!(
            "problem capture response top-level fields must be exactly: boundary"
        ));
    }

    let boundary = top
        .get("boundary")
        .and_then(Value::as_object)
        .ok_or_else(|| anyhow!("boundary must be an object"))?;

    if boundary.len() != 1 || !boundary.contains_key("problem") {
        return Err(anyhow!(
            "problem capture response boundary fields must be exactly: problem"
        ));
    }

    boundary
        .get("problem")
        .and_then(Value::as_str)
        .ok_or_else(|| anyhow!("boundary.problem must be a string"))?;

    Ok(response)
}

#[cfg(test)]
mod tests {
    use super::validate_problem_capture_response;
    use serde_json::json;

    #[test]
    fn validate_problem_capture_response_accepts_valid_problem() {
        let response = json!({
            "boundary": {
                "problem": "知识和信息分散，难以持续组织、关联和复用"
            }
        });

        let validated =
            validate_problem_capture_response(response.clone()).expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_problem_capture_response_accepts_empty_problem() {
        let response = json!({
            "boundary": {
                "problem": ""
            }
        });

        let validated =
            validate_problem_capture_response(response.clone()).expect("expected valid payload");
        assert_eq!(validated, response);
    }

    #[test]
    fn validate_problem_capture_response_rejects_missing_problem() {
        let response = json!({
            "boundary": {}
        });

        let err = validate_problem_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("problem capture response boundary fields must be exactly: problem")
        );
    }

    #[test]
    fn validate_problem_capture_response_rejects_extra_top_level_field() {
        let response = json!({
            "boundary": {
                "problem": "软件开发过程中上下文切换频繁，导致开发效率下降"
            },
            "extra": {}
        });

        let err = validate_problem_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("problem capture response top-level fields must be exactly: boundary")
        );
    }

    #[test]
    fn validate_problem_capture_response_rejects_extra_boundary_field() {
        let response = json!({
            "boundary": {
                "problem": "语言学习难以长期坚持和持续积累",
                "extra": "x"
            }
        });

        let err = validate_problem_capture_response(response).expect_err("expected error");
        assert!(
            err.to_string()
                .contains("problem capture response boundary fields must be exactly: problem")
        );
    }
}
