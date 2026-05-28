use anyhow::{anyhow, bail, Result};
use serde_json::Value;

use crate::mutation::json_read::path_to_string;

pub fn set_value_at_path(
    root: &mut Value,
    path: &[String],
    new_value: Value,
) -> Result<()> {
    if path.is_empty() {
        bail!("set operation cannot target <root>");
    }

    let mut current = root;

    for segment in &path[..path.len() - 1] {
        let object = current.as_object_mut().ok_or_else(|| {
            anyhow!(
                "cannot set path {}; segment {:?} requires object",
                path_to_string(path),
                segment
            )
        })?;

        current = object.get_mut(segment).ok_or_else(|| {
            anyhow!(
                "cannot set path {}; segment {:?} does not exist",
                path_to_string(path),
                segment
            )
        })?;
    }

    let final_segment = path
        .last()
        .expect("path is already checked to be non-empty");

    let object = current.as_object_mut().ok_or_else(|| {
        anyhow!(
            "cannot set path {}; parent of {:?} is not an object",
            path_to_string(path),
            final_segment
        )
    })?;

    if !object.contains_key(final_segment) {
        bail!(
            "cannot set path {}; field {:?} does not exist",
            path_to_string(path),
            final_segment
        );
    }

    object.insert(final_segment.clone(), new_value);

    Ok(())
}
