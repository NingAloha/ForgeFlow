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

pub fn remove_string_from_list_at_path(
    root: &mut Value,
    path: &[String],
    target: &str,
) -> Result<()> {
    let value = get_value_mut_at_path(root, path)?;

    let array = value.as_array_mut().ok_or_else(|| {
        anyhow!(
            "cannot remove from path {}; target is not an array",
            path_to_string(path)
        )
    })?;

    let original_len = array.len();

    array.retain(|item| item.as_str() != Some(target));

    if array.len() == original_len {
        bail!(
            "cannot remove {:?} from path {}; value not found",
            target,
            path_to_string(path)
        );
    }

    Ok(())
}

fn get_value_mut_at_path<'a>(
    root: &'a mut Value,
    path: &[String],
) -> Result<&'a mut Value> {
    if path.is_empty() {
        return Ok(root);
    }

    let mut current = root;

    for segment in path {
        let object = current.as_object_mut().ok_or_else(|| {
            anyhow!(
                "cannot access path {}; segment {:?} requires object",
                path_to_string(path),
                segment
            )
        })?;

        current = object.get_mut(segment).ok_or_else(|| {
            anyhow!(
                "cannot access path {}; segment {:?} does not exist",
                path_to_string(path),
                segment
            )
        })?;
    }

    Ok(current)
}