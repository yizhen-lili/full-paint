import { useMutation } from '@tanstack/vue-query'

import { getPaintRequirements } from './api'

/** lazy 查詢：用 mutation（按按鈕觸發）而非 useQuery（reactive auto-run），
 *  避免使用者打字選規格時就頻繁戳後端。 */
export function usePaintRequirementsMutation() {
  return useMutation({
    mutationFn: (params: { variantId: string; quantity: number }) =>
      getPaintRequirements(params.variantId, params.quantity),
  })
}
