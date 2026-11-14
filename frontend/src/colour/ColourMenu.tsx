import { Check, Palette } from 'lucide-react'
import { useRef, useState } from 'react'
import type { ReactElement } from 'react'
import type { MapData } from '../map/mapData'
import { Popover } from '../popover/Popover'
import { shownProbes } from '../probes/levels'
import { ProbeList } from '../probes/ProbeList'
import type { Colouring } from './legend'

interface ColourMenuProps {
  data: MapData
  choice: Colouring
  /** Composed colours are on: the menu shows no choice as current until they are left. */
  composed: boolean
  hasDates: boolean
  onChoose(colouring: Colouring): void
}

interface Option {
  id: string
  label: string
  colouring: Colouring
  disabled: string | null
}

/** The attribute that colours every point of the map: a column, the date, or the level a probe reads. */
export function ColourMenu({ data, choice, composed, hasDates, onChoose }: ColourMenuProps): ReactElement {
  const trigger = useRef<HTMLButtonElement>(null)
  const [open, setOpen] = useState(false)
  const options: Option[] = [
    ...data.columns.map((column) => ({
      id: column.key,
      label: column.label,
      colouring: { kind: 'column', key: column.key } as const,
      disabled: null,
    })),
    { id: 'date', label: 'Date', colouring: { kind: 'date' } as const, disabled: hasDates ? null : 'No item of this map is dated.' },
  ]
  const current = composed ? null : choice.kind === 'date' ? 'date' : choice.kind === 'column' ? choice.key : null
  const probe = !composed && choice.kind === 'probe' ? choice.key : null
  const hasProbes = shownProbes(data.probes).length > 0

  return (
    <>
      <button
        ref={trigger}
        type="button"
        className="nm-tool nm-tool--icon"
        title="Colour by"
        aria-label="Colour by"
        aria-haspopup="dialog"
        aria-expanded={open}
        data-tour="colour"
        onClick={() => setOpen((value) => !value)}
      >
        <Palette size={17} aria-hidden />
      </button>
      <Popover anchor={trigger} open={open} onClose={() => setOpen(false)} variant="menu" width={hasProbes ? 300 : 220} label="Colour by">
        <p className="nm-menu-title">Colour by</p>
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            className={`nm-menu-row${current === option.id ? ' is-chosen' : ''}`}
            disabled={option.disabled !== null}
            title={option.disabled ?? undefined}
            onClick={() => {
              onChoose(option.colouring)
              setOpen(false)
            }}
          >
            <span className="nm-menu-row__label">{option.label}</span>
            {current === option.id ? <Check size={13} aria-hidden /> : null}
          </button>
        ))}
        <div className="nm-menu-sep" />
        <p className="nm-menu-title" title="Each item takes the colour of the level a probe reads for it: not flagged, possible or probable.">
          Probe level
        </p>
        <div className="nm-menu-probes">
          <ProbeList
            probes={data.probes}
            current={probe}
            onPick={(picked) => {
              onChoose({ kind: 'probe', key: picked.key })
              setOpen(false)
            }}
          />
        </div>
      </Popover>
    </>
  )
}
