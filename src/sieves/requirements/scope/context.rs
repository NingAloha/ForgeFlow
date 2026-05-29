use anyhow::{anyhow, Result};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScopeSieveEntryTrigger {
    PendingClarification { pending_id: String },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ScopeSieveRunContext {
    pub trigger: ScopeSieveEntryTrigger,
    pub related_inconsistency_id: Option<String>,
}

impl ScopeSieveRunContext {
    pub fn pending_clarification(pending_id: impl Into<String>) -> Self {
        Self {
            trigger: ScopeSieveEntryTrigger::PendingClarification {
                pending_id: pending_id.into(),
            },
            related_inconsistency_id: None,
        }
    }

    pub fn pending_clarification_with_inconsistency(
        pending_id: impl Into<String>,
        inconsistency_id: impl Into<String>,
    ) -> Self {
        Self {
            trigger: ScopeSieveEntryTrigger::PendingClarification {
                pending_id: pending_id.into(),
            },
            related_inconsistency_id: Some(inconsistency_id.into()),
        }
    }
}

pub fn require_pending_clarification_trigger(
    context: &ScopeSieveRunContext,
    expected_pending_id: &str,
) -> Result<()> {
    match &context.trigger {
        ScopeSieveEntryTrigger::PendingClarification { pending_id } => {
            if pending_id == expected_pending_id {
                Ok(())
            } else {
                Err(anyhow!(
                    "invalid pending clarification trigger: expected {}, got {}",
                    expected_pending_id,
                    pending_id
                ))
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{
        require_pending_clarification_trigger,
        ScopeSieveEntryTrigger,
        ScopeSieveRunContext,
    };

    #[test]
    fn pending_clarification_creates_expected_trigger() {
        let context = ScopeSieveRunContext::pending_clarification("product.target_users");
        assert_eq!(
            context.trigger,
            ScopeSieveEntryTrigger::PendingClarification {
                pending_id: "product.target_users".to_string(),
            }
        );
        assert_eq!(context.related_inconsistency_id, None);
    }

    #[test]
    fn pending_clarification_with_inconsistency_stores_related_id() {
        let context = ScopeSieveRunContext::pending_clarification_with_inconsistency(
            "product.target_users",
            "product.target_users.unclear_target_users",
        );
        assert_eq!(
            context.trigger,
            ScopeSieveEntryTrigger::PendingClarification {
                pending_id: "product.target_users".to_string(),
            }
        );
        assert_eq!(
            context.related_inconsistency_id,
            Some("product.target_users.unclear_target_users".to_string())
        );
    }

    #[test]
    fn require_pending_clarification_trigger_accepts_match() {
        let context = ScopeSieveRunContext::pending_clarification("product.target_users");
        require_pending_clarification_trigger(&context, "product.target_users")
            .expect("matching pending id should pass");
    }

    #[test]
    fn require_pending_clarification_trigger_rejects_mismatch() {
        let context = ScopeSieveRunContext::pending_clarification("scope.capability_categories");
        let err = require_pending_clarification_trigger(&context, "product.target_users")
            .expect_err("mismatched pending id should fail");
        assert_eq!(
            err.to_string(),
            "invalid pending clarification trigger: expected product.target_users, got scope.capability_categories"
        );
    }
}
