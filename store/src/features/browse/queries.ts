import { useQuery } from '@tanstack/vue-query'
import { listThemes, listSeries, listTags } from './api'

const STALE_10MIN = 10 * 60 * 1000

/** Themes — stale 10 分鐘（主題不常變） */
export function useThemesQuery() {
  return useQuery({
    queryKey: ['public', 'themes'],
    queryFn: listThemes,
    staleTime: STALE_10MIN,
  })
}

/** Series — 全部系列；mega-menu / 主題詳情頁共用 */
export function useSeriesQuery(themeId?: string) {
  return useQuery({
    queryKey: ['public', 'series', themeId ?? null],
    queryFn: () => listSeries(themeId),
    staleTime: STALE_10MIN,
  })
}

/** Tags — 標籤清單，mega-menu / 商品列表 filter 共用 */
export function useTagsQuery() {
  return useQuery({
    queryKey: ['public', 'tags'],
    queryFn: listTags,
    staleTime: STALE_10MIN,
  })
}
