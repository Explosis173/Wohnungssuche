import { onBeforeUnmount, onMounted, ref } from 'vue'

const DETAIL_PREFIX = '#/l/'

/** Minimal hash routing: "#/l/<id>" opens a listing, anything else the list. */
export function useHashRoute() {
  const selectedId = ref<string | null>(parse())
  // Only go "back" if the detail was opened from the list – not when the app
  // was launched directly on a listing (e.g. from a push notification).
  let openedFromList = false

  function parse(): string | null {
    const hash = window.location.hash
    return hash.startsWith(DETAIL_PREFIX) ? decodeURIComponent(hash.slice(DETAIL_PREFIX.length)) : null
  }

  function sync(): void {
    selectedId.value = parse()
  }

  function open(id: string): void {
    openedFromList = true
    window.location.hash = `${DETAIL_PREFIX}${encodeURIComponent(id)}`
  }

  function close(): void {
    if (openedFromList) window.history.back()
    else window.location.hash = ''
    openedFromList = false
  }

  onMounted(() => window.addEventListener('hashchange', sync))
  onBeforeUnmount(() => window.removeEventListener('hashchange', sync))

  return { selectedId, open, close }
}
