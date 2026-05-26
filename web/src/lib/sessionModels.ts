import type { SessionState } from "./types";

function getSessionModelOptions(
  session: SessionState | null | undefined,
  selectedKey: "new_api_image_model" | "new_api_text_model",
  listKey: "new_api_image_models" | "new_api_text_models",
): string[] {
  const models: string[] = [];
  const addModel = (value: string | null | undefined) => {
    const normalized = value?.trim();
    if (normalized && !models.includes(normalized)) {
      models.push(normalized);
    }
  };
  addModel(session?.[selectedKey]);
  session?.[listKey]?.forEach(addModel);
  return models;
}

export function getSessionImageModelOptions(session: SessionState | null | undefined): string[] {
  return getSessionModelOptions(session, "new_api_image_model", "new_api_image_models");
}

export function getSessionTextModelOptions(session: SessionState | null | undefined): string[] {
  return getSessionModelOptions(session, "new_api_text_model", "new_api_text_models");
}
