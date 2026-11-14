import { CalendarArrowDown, CalendarArrowUp, ListFilter, MoreHorizontal, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import { ItemList } from '../items/ItemList'
import type { MapData } from '../map/mapData'
import '../neighbours/drawers.css'
import { Popover } from '../popover/Popover'
import { plural } from '../text/format'
import { VoicesCheck } from '../voices/VoicesCheck'

const SORT_KEY = 'noisemap.selection.newestFirst'

export interface SelectionAction {
  id: string
  label: string
  /** Why the action cannot run, when it cannot. */
  disabled: string | null
  run(): void
}

interface SelectionDrawerProps {
  data: MapData
  indices: Uint32Array
  actions: SelectionAction[]
  onKeepInFilters(): void
  onShow(index: number): void
  onOpen(index: number): void
  onRing(index: number | null): void
  /** Closes the list; the selection stays lit. */
  onClose(): void
}

function storedSort(): boolean {
  try {
    return localStorage.getItem(SORT_KEY) === '1'
  } catch {
    return false
  }
}

/** The items chosen with the lasso, as a list, with what can be done with them. */
export function SelectionDrawer(props: SelectionDrawerProps): ReactElement {
  const { data, indices, actions, onKeepInFilters, onShow, onOpen, onRing, onClose } = props
  const [newestFirst, setNewestFirst] = useState(storedSort)
  const [menu, setMenu] = useState(false)
  const more = useRef<HTMLButtonElement>(null)

  const sorted = useMemo(() => {
    const dated = (index: number): boolean => data.ts[index] > 0
    return Array.from(indices).sort((a, b) => {
      // Undated items go last in both orders.
      if (dated(a) !== dated(b)) return dated(a) ? -1 : 1
      return newestFirst ? data.ts[b] - data.ts[a] : data.ts[a] - data.ts[b]
    })
  }, [data, indices, newestFirst])

  const flip = (): void => {
    setNewestFirst((value) => {
      try {
        localStorage.setItem(SORT_KEY, value ? '0' : '1')
      } catch {
        // Not remembered.
      }
      return !value
    })
  }

  return (
    <aside className="nm-drawer nm-drawer--selection" aria-label="Selected items">
      <header className="nm-drawer__head">
        <h2>{plural(indices.length, 'selected item', 'selected items')}</h2>
        <button type="button" className="nm-drawer__icon" onClick={flip} title={newestFirst ? 'Newest first. Click for oldest first.' : 'Oldest first. Click for newest first.'} aria-label="Change the order">
          {newestFirst ? <CalendarArrowDown size={15} aria-hidden /> : <CalendarArrowUp size={15} aria-hidden />}
        </button>
        <button type="button" className="nm-drawer__icon" onClick={onKeepInFilters} title="Keep only these items on the map" aria-label="Keep in the filters">
          <ListFilter size={15} aria-hidden />
        </button>
        <button ref={more} type="button" className="nm-drawer__icon" onClick={() => setMenu((value) => !value)} title="More actions" aria-label="More actions" aria-haspopup="dialog" aria-expanded={menu}>
          <MoreHorizontal size={15} aria-hidden />
        </button>
        <button type="button" className="nm-drawer__icon" onClick={onClose} title="Close the list (the selection stays)" aria-label="Close">
          <X size={15} aria-hidden />
        </button>
      </header>
      <Popover anchor={more} open={menu} onClose={() => setMenu(false)} variant="menu" width={268} label="More actions">
        {actions.map((action) => (
          <button
            key={action.id}
            type="button"
            className="nm-menu-row"
            disabled={action.disabled !== null}
            title={action.disabled ?? undefined}
            onClick={() => {
              setMenu(false)
              action.run()
            }}
          >
            <span className="nm-menu-row__label">{action.label}</span>
          </button>
        ))}
      </Popover>
      <VoicesCheck indices={indices} onOpen={onOpen} />
      <ItemList
        data={data}
        indices={sorted}
        listKey={`selection:${indices.length}:${indices[0] ?? 0}:${newestFirst ? 'new' : 'old'}`}
        onShow={onShow}
        onOpen={onOpen}
        onRing={onRing}
      />
    </aside>
  )
}
