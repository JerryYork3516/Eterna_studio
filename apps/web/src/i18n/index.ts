import en from "../../locales/en.json";
import zh from "../../locales/zh.json";

export const languages = ["zh", "en"] as const;
export type Language = (typeof languages)[number];

const dictionaries: Record<Language, Record<string, string>> = { zh, en };

export function translate(language: Language, key: string, fallback?: string) {
  return dictionaries[language][key] ?? fallback ?? key;
}

export function isLanguage(value: string): value is Language {
  return languages.includes(value as Language);
}
