"use client";
import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api-client";
import type { Api } from "@aureon/shared-types";

type NaturalLanguageIn = Api.NaturalLanguageIn;
type NaturalLanguagePreviewOut = Api.NaturalLanguagePreviewOut;

/**
 * EP-DC-38 C2 natural-language capture (R-DEC-96/97). One mutation per submit; a fresh
 * Idempotency-Key is attached by `apiRequest({idempotent:true})`. The response is a NOT-committed
 * preview — task creation is a separate, chair-approved step.
 */
export function useNaturalLanguage() {
  return useMutation<NaturalLanguagePreviewOut, unknown, NaturalLanguageIn>({
    mutationFn: async (input) => {
      const res = await apiRequest<NaturalLanguagePreviewOut>("/data-capture/natural-language", {
        method: "POST",
        body: input,
        idempotent: true,
      });
      return res.data;
    },
  });
}
