import type { ComputedRef } from "vue";
import {
  effectiveLocale,
  rememberLocale,
  restoreLocale,
  translate,
  validLocale,
  type Locale,
  type MessageKey,
} from "~/utils/locale";

export function useLocale(staff?: ComputedRef<boolean>) {
  const preference = useState<Locale>("applicant-language", () => "zh");
  const restored = useState<boolean>(
    "applicant-language-restored",
    () => false,
  );
  const locale = computed(() =>
    effectiveLocale(preference.value, !!staff?.value),
  );
  onMounted(() => {
    if (restored.value) return;
    try {
      preference.value = restoreLocale(window.localStorage);
    } catch {
      preference.value = "zh";
    }
    restored.value = true;
  });
  function setLocale(value: Locale) {
    if (staff?.value) return;
    try {
      preference.value = rememberLocale(window.localStorage, value);
    } catch {
      preference.value = validLocale(value);
    }
  }
  return {
    locale,
    setLocale,
    t: (key: MessageKey | "") => translate(key, locale.value),
  };
}
