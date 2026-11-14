import { ClipboardPaste } from 'lucide-react'
import type { ReactElement } from 'react'
import { AxesMenu } from '../axes/AxesMenu'
import { ColourMenu } from '../colour/ColourMenu'
import { FilterBar } from '../filters/FilterBar'
import { useTheme } from '../theme/theme'
import { DisplayMenu } from '../toolbar/DisplayMenu'
import { Toolbar } from '../toolbar/Toolbar'
import type { MapData } from './mapData'
import type { MapActions } from './useMapActions'
import type { MapModel } from './useMapModel'

interface MapBarProps {
  data: MapData
  model: MapModel
  actions: MapActions
  lasso: boolean
  /** Lines from the selected point to its neighbours are drawn. */
  edges: boolean
  composing: boolean
  pasting: boolean
  onLasso(on: boolean): void
  onEdges(on: boolean): void
  onComposing(open: boolean): void
  onPasting(open: boolean): void
}

/** The bar above the map: filters and search on the left, the paste box, then the tools. */
export function MapBar(props: MapBarProps): ReactElement {
  const { data, model, actions, lasso, edges, composing, pasting } = props
  const { colouring, scrubber, shape, relief, range, kept, filters } = model
  const [theme, toggleTheme] = useTheme()
  const noDates = range ? null : 'No item of this map is dated.'

  return (
    <FilterBar
      data={data}
      range={range}
      filters={filters}
      onFilters={model.setFilters}
      onPick={actions.goTo}
      onLift={actions.liftConcept}
      beside={
        <button
          type="button"
          className={`nm-tool${pasting ? ' is-active' : ''}`}
          aria-pressed={pasting}
          title="Place a text or the page behind a link on the map"
          data-tour="paste"
          onClick={() => props.onPasting(!pasting)}
        >
          <ClipboardPaste size={13} aria-hidden />
          Paste a text or a link
        </button>
      }
      tools={
        <Toolbar
          shown={kept.shown}
          total={data.n}
          shape={shape}
          lasso={lasso}
          composing={composing}
          composed={colouring.composed !== null}
          onFlat={(flat) => model.setShape(flat ? '2d' : '3d')}
          onLasso={props.onLasso}
          onCompose={props.onComposing}
          colourMenu={<ColourMenu data={data} choice={colouring.choice} composed={colouring.composed !== null} hasDates={range !== null} onChoose={colouring.choose} />}
          axesMenu={
            <AxesMenu
              shape={shape}
              relief={relief}
              probes={data.probes}
              hasDates={range !== null}
              busy={actions.busy}
              error={actions.error}
              onShape={model.setShape}
              onProbe={actions.liftProbe}
              onConcept={actions.liftConcept}
              onClearRelief={() => model.setRelief(null)}
            />
          }
          displayMenu={
            <DisplayMenu
              options={[
                { id: 'scrubber', label: 'Time window', hint: 'A window over the dates: the items inside stay lit', on: scrubber.on, disabled: noDates, set: scrubber.setOn },
                { id: 'edges', label: 'Lines to neighbours', hint: 'Lines from the selected item to its nearest by meaning', on: edges, disabled: null, set: props.onEdges },
                { id: 'dark', label: 'Dark theme', hint: 'Light or dark', on: theme === 'dark', disabled: null, set: toggleTheme },
              ]}
            />
          }
        />
      }
    />
  )
}
