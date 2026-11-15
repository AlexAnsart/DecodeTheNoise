import type { ReactElement, RefObject } from 'react'
import { maskOfIndices } from '../colour/emphasis'
import { NeighbourDrawer } from '../neighbours/NeighbourDrawer'
import { SelectionDrawer } from '../selection/SelectionDrawer'
import { useSelectionReview } from '../selection/useSelectionReview'
import { plural } from '../text/format'
import type { MapData } from './mapData'
import type { MapActions } from './useMapActions'
import type { MapModel } from './useMapModel'

interface MapDrawersProps {
  data: MapData
  /** The box of the drawers: its width is the part of the stage they cover. */
  drawers: RefObject<HTMLDivElement | null>
  model: MapModel
  actions: MapActions
  /** Neighbours of the selected point, when their list is open. */
  neighbours: number[] | null
  /** Nearest items of the pasted text, while it is open. */
  pastedNeighbours: number[] | null
  /** The lasso selection, when its list is open. */
  listed: Uint32Array | null
  /** Brings a point into view without selecting it. */
  onShow(index: number): void
  onRing(index: number | null): void
  onCloseNeighbours(): void
  onClosePasted(): void
  onCloseList(): void
}

/** The lists that open on the right of the map: neighbours of a point, of a pasted text, and
 *  the items chosen with the lasso. */
export function MapDrawers(props: MapDrawersProps): ReactElement {
  const { data, drawers, model, actions, neighbours, pastedNeighbours, listed, onShow, onRing } = props
  const { selected, colouring, filters } = model
  // Held here, above the list of the selection: closing the list neither stops nor loses it.
  const review = useSelectionReview(model.picked)

  return (
    <div ref={drawers} className="nm-drawers">
      {neighbours && selected !== null ? (
        <NeighbourDrawer
          data={data}
          listKey={`neighbours:${selected}`}
          neighbours={neighbours}
          onShow={onShow}
          onOpen={actions.goTo}
          onRing={onRing}
          onClose={props.onCloseNeighbours}
        />
      ) : null}
      {pastedNeighbours ? (
        <NeighbourDrawer
          data={data}
          listKey={`neighbours:pasted:${pastedNeighbours.join('-')}`}
          neighbours={pastedNeighbours}
          onShow={onShow}
          onOpen={actions.goTo}
          onRing={onRing}
          onClose={props.onClosePasted}
        />
      ) : null}
      {listed ? (
        <SelectionDrawer
          data={data}
          indices={listed}
          review={review}
          actions={[
            { id: 'likeness', label: 'Raise what resembles this selection', disabled: actions.busy ? 'A score is being computed.' : null, run: actions.liftSelection },
            { id: 'colour', label: 'Colour this selection against the rest', disabled: null, run: () => colouring.compose([{ label: 'The selection', mask: maskOfIndices(data.n, listed) }]) },
            { id: 'clear', label: 'Clear the selection', disabled: null, run: () => model.setPicked(null) },
          ]}
          onKeepInFilters={() => {
            model.setFilters({ ...filters, kept: { label: plural(listed.length, 'selected item', 'selected items'), mask: maskOfIndices(data.n, listed) } })
            props.onCloseList()
          }}
          onShow={onShow}
          onOpen={actions.goTo}
          onRing={onRing}
          onClose={props.onCloseList}
        />
      ) : null}
    </div>
  )
}
