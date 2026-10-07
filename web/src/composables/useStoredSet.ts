import { ref, watch, type Ref } from 'vue'

/** A set of ids remembered on this device (favorites, hidden listings). */
export function useStoredSet(key: string): { set: Ref<Set<string>>; toggle: (id: string) => void } {
  const set = ref<Set<string>>(new Set(read(key)))

  watch(
    set,
    (value) => {
      try {
        localStorage.setItem(key, JSON.stringify([...value]))
      } catch {
        // Private mode or blocked storage: keep working in memory only.
      }
    },
    { deep: true },
  )

  function toggle(id: string): void {
    const next = new Set(set.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    set.value = next
  }

  return { set, toggle }
}

function read(key: string): string[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter((v): v is string => typeof v === 'string') : []
  } catch {
    return []
  }
}
