use serde_json::{Value, json};

pub fn is_blank(value: &str) -> bool {
    value.trim().is_empty()
}

pub fn is_candidate_complete(domain: &str, problem: &str, core_approach: &str) -> bool {
    !is_blank(domain) && !is_blank(problem) && !is_blank(core_approach)
}

pub fn merge_domain_and_problem_candidate(
    domain_candidate: &Value,
    problem_candidate: &Value,
) -> Result<Value, String> {
    let raw_input = domain_candidate
        .get("origin")
        .and_then(|v| v.get("raw_input"))
        .and_then(Value::as_str)
        .ok_or_else(|| "domain candidate missing origin.raw_input".to_string())?;

    let domain = domain_candidate
        .get("boundary")
        .and_then(|v| v.get("domain"))
        .and_then(Value::as_str)
        .ok_or_else(|| "domain candidate missing boundary.domain".to_string())?;

    let problem = problem_candidate
        .get("boundary")
        .and_then(|v| v.get("problem"))
        .and_then(Value::as_str)
        .ok_or_else(|| "problem candidate missing boundary.problem".to_string())?;

    Ok(json!({
        "origin": {
            "raw_input": raw_input
        },
        "boundary": {
            "domain": domain,
            "problem": problem
        }
    }))
}

pub fn build_boundary_preview(domain: &str, problem: &str, core_approach: &str) -> String {
    if is_blank(domain) {
        return "我还无法确定这个项目所属的工具领域。\n请补充：这个项目主要属于哪类工具或使用场景？".to_string();
    }

    if is_blank(problem) {
        return format!(
            "已识别领域：{}\n我还无法确定这个项目最想解决的核心问题。\n请补充：这个项目主要想解决什么问题？",
            domain
        );
    }

    if is_blank(core_approach) {
        return format!(
            "已识别领域：{}\n已识别核心问题：{}\n\n我还无法确定这个项目解决核心问题所采用的核心解法。\n请补充：这个项目主要通过什么方式解决上述问题？",
            domain, problem
        );
    }

    format!(
        "我理解这个项目大概是：\n1. 领域：{}\n2. 核心问题：{}\n3. 核心解法：{}\n这些理解是否一致？",
        domain, problem, core_approach
    )
}

#[cfg(test)]
mod tests {
    use super::{
        build_boundary_preview, is_candidate_complete, merge_domain_and_problem_candidate,
    };
    use serde_json::json;

    #[test]
    fn preview_enters_confirmation_with_core_approach_when_all_present() {
        let text = build_boundary_preview(
            "软件开发工具",
            "软件开发过程中上下文切换频繁，导致开发效率下降",
            "通过命令行 Agent 理解项目上下文并协助修改代码",
        );
        assert!(text.contains("这些理解是否一致？"));
        assert!(text.contains("1. 领域：软件开发工具"));
        assert!(text.contains("2. 核心问题：软件开发过程中上下文切换频繁，导致开发效率下降"));
        assert!(text.contains("3. 核心解法：通过命令行 Agent 理解项目上下文并协助修改代码"));
        assert!(!text.contains("核心能力"));
    }

    #[test]
    fn preview_prompts_missing_problem_when_problem_is_blank() {
        let text = build_boundary_preview("软件开发工具", "   ", "通过自然语言辅助软件开发");
        assert!(text.contains("已识别领域：软件开发工具"));
        assert!(text.contains("请补充：这个项目主要想解决什么问题？"));
        assert!(!text.contains("这些理解是否一致？"));
        assert!(!text.contains("2. 核心问题："));
    }

    #[test]
    fn preview_prompts_missing_domain_when_domain_is_blank() {
        let text = build_boundary_preview(
            "   ",
            "软件开发过程中上下文切换频繁，导致开发效率下降",
            "通过自然语言辅助软件开发",
        );
        assert!(text.contains("请补充：这个项目主要属于哪类工具或使用场景？"));
        assert!(!text.contains("这些理解是否一致？"));
        assert!(!text.contains("1. 领域："));
    }

    #[test]
    fn preview_prompts_when_domain_and_problem_are_blank() {
        let text = build_boundary_preview("   ", "   ", "通过自然语言辅助软件开发");
        assert!(text.contains("我还无法确定这个项目所属的工具领域。"));
        assert!(!text.contains("这些理解是否一致？"));
        assert!(!text.contains("1. 领域："));
        assert!(!text.contains("2. 核心问题："));
    }

    #[test]
    fn preview_prompts_missing_core_approach_when_core_approach_is_blank() {
        let text = build_boundary_preview("软件开发工具", "上下文切换频繁导致效率下降", "  ");
        assert!(text.contains("已识别领域：软件开发工具"));
        assert!(text.contains("已识别核心问题：上下文切换频繁导致效率下降"));
        assert!(text.contains("请补充：这个项目主要通过什么方式解决上述问题？"));
        assert!(!text.contains("这些理解是否一致？"));
        assert!(!text.contains("3. 核心解法："));
        assert!(!text.contains("核心能力"));
    }

    #[test]
    fn preview_with_multiple_missing_fields_does_not_enter_confirmation() {
        let text = build_boundary_preview("   ", "   ", "   ");
        assert!(!text.contains("这些理解是否一致？"));
    }

    #[test]
    fn merge_candidate_uses_same_round_domain_and_problem() {
        let domain_candidate = json!({
            "origin": { "raw_input": "做一个 gpt客户端" },
            "boundary": { "domain": "AI工具" }
        });
        let problem_candidate = json!({
            "boundary": { "problem": "用户难以便捷、高效地与 GPT 模型进行交互" }
        });

        let merged = merge_domain_and_problem_candidate(&domain_candidate, &problem_candidate)
            .expect("should merge");
        assert_eq!(merged["origin"]["raw_input"], "做一个 gpt客户端");
        assert_eq!(merged["boundary"]["domain"], "AI工具");
        assert_eq!(
            merged["boundary"]["problem"],
            "用户难以便捷、高效地与 GPT 模型进行交互"
        );
    }

    #[test]
    fn incomplete_candidate_is_not_complete() {
        assert!(!is_candidate_complete("AI工具", "问题", "   "));
        assert!(!is_candidate_complete("AI工具", "   ", "核心解法"));
        assert!(!is_candidate_complete("   ", "问题", "核心解法"));
        assert!(!is_candidate_complete("   ", "   ", "核心解法"));
        assert!(is_candidate_complete("AI工具", "问题", "核心解法"));
    }
}
