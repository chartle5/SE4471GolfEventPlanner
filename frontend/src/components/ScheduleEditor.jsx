import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from '@dnd-kit/core'
import {
  SortableContext,
  useSortable,
  arrayMove,
  verticalListSortingStrategy,
  sortableKeyboardCoordinates,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import Icon from './Icon'

const PLACEHOLDER_RE = /^Player \d+$/

/**
 * Drag-and-drop tee-schedule editor.
 *
 * Players registered on the same team are bundled into a single draggable
 * "unit" (a coloured block) so partners can never be separated — dragging the
 * block moves all teammates together. Individuals and unclaimed placeholders are
 * single-player units. Reordering is allowed within and across tee groups; the
 * backend re-validates that no player is added/removed and that teams stay
 * grouped before persisting.
 */
export default function ScheduleEditor({ schedule, teamMap, onSave, saving }) {
  // Serialised signature of the incoming schedule, to know when to re-seed.
  const signature = useMemo(
    () => JSON.stringify((schedule || []).map(g => [g.group, g.teeTime, g.players])),
    [schedule]
  )

  const seed = useMemo(() => buildUnits(schedule || [], teamMap || {}), [signature, teamMap])

  const [containers, setContainers] = useState(seed.containers)
  const [dirty, setDirty] = useState(false)
  const [activeId, setActiveId] = useState(null)
  const [warning, setWarning] = useState('')
  const lastSignature = useRef(signature)

  // Re-seed from props when the upstream schedule changes and we have no
  // unsaved edits (avoids clobbering in-progress reordering on the 15s poll).
  useEffect(() => {
    if (signature !== lastSignature.current && !dirty) {
      setContainers(seed.containers)
      lastSignature.current = signature
    } else if (signature !== lastSignature.current && dirty) {
      lastSignature.current = signature // remember it; user keeps their edits
    }
  }, [signature, dirty, seed])

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  const { unitsById, meta, order } = seed

  function findContainer(id) {
    if (id in containers) return id
    return order.find(cid => containers[cid]?.includes(id))
  }

  function handleDragStart(event) {
    setActiveId(event.active.id)
    setWarning('')
  }

  // Cross-group moves are swaps, not transfers: dropping unit A onto unit B in a
  // different group exchanges their slots, so every tee group keeps its size. A
  // swap is only valid when both units hold the same number of players (e.g. two
  // singles, or two pairs); otherwise the group sizes would change, so we reject
  // it and tell the user to swap with a matching player/team instead.
  function handleDragEnd(event) {
    const { active, over } = event
    setActiveId(null)
    if (!over) return

    const activeContainer = findContainer(active.id)
    const overIsContainer = over.id in containers
    const overContainer = overIsContainer ? over.id : findContainer(over.id)
    if (!activeContainer || !overContainer) return

    // Reordering within the same tee group is always fine.
    if (activeContainer === overContainer) {
      const items = containers[activeContainer]
      const oldIndex = items.indexOf(active.id)
      const newIndex = overIsContainer ? items.length - 1 : items.indexOf(over.id)
      if (oldIndex !== newIndex && newIndex !== -1) {
        setContainers(prev => ({ ...prev, [activeContainer]: arrayMove(prev[activeContainer], oldIndex, newIndex) }))
        setDirty(true)
        setWarning('')
      }
      return
    }

    // Cross-group: must be dropped directly onto a unit to swap with.
    if (overIsContainer) {
      setWarning('To move someone to another tee time, drop them directly onto a player or team to swap places — groups must stay the same size.')
      return
    }

    const dragged = unitsById[active.id]
    const target = unitsById[over.id]
    if (!dragged || !target) return

    if (dragged.players.length !== target.players.length) {
      const fmt = (n) => `${n} player${n === 1 ? '' : 's'}`
      setWarning(`Can't swap ${fmt(dragged.players.length)} with ${fmt(target.players.length)} — that would change the tee group sizes. Swap with a player or team of the same size instead.`)
      return
    }

    // Equal-size swap: exchange the two units between their groups.
    setContainers(prev => {
      const fromItems = [...prev[activeContainer]]
      const toItems = [...prev[overContainer]]
      const fromIdx = fromItems.indexOf(active.id)
      const toIdx = toItems.indexOf(over.id)
      if (fromIdx === -1 || toIdx === -1) return prev
      fromItems[fromIdx] = over.id
      toItems[toIdx] = active.id
      return { ...prev, [activeContainer]: fromItems, [overContainer]: toItems }
    })
    setDirty(true)
    setWarning('')
  }

  function buildSchedule() {
    return order.map(cid => ({
      group: meta[cid].group,
      teeTime: meta[cid].teeTime,
      players: containers[cid].flatMap(uid => unitsById[uid].players),
    }))
  }

  function handleReset() {
    setContainers(seed.containers)
    setDirty(false)
    setWarning('')
    lastSignature.current = signature
  }

  async function handleSave() {
    const ok = await onSave(buildSchedule())
    if (ok) setDirty(false)
  }

  const activeUnit = activeId ? unitsById[activeId] : null

  return (
    <div>
      <div className="notice notice-info" style={{ margin: '0 22px 16px' }}>
        <Icon name="users" size={16} style={{ flexShrink: 0, marginTop: 1 }} />
        <span>
          Reorder within a tee group freely. To move someone to a different tee
          time, drop them onto a player or team of the same size to swap places —
          this keeps every group at its set size. Teammates are locked together
          (gold blocks) and always move as one.
        </span>
      </div>

      {warning && (
        <div className="notice notice-warn" style={{ margin: '0 22px 16px' }}>
          <Icon name="users" size={16} style={{ flexShrink: 0, marginTop: 1 }} />
          <span>{warning}</span>
        </div>
      )}

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 14,
          padding: '0 22px',
        }}>
          {order.map(cid => (
            <GroupColumn
              key={cid}
              id={cid}
              meta={meta[cid]}
              unitIds={containers[cid]}
              unitsById={unitsById}
            />
          ))}
        </div>

        <DragOverlay>
          {activeUnit ? <UnitChip unit={activeUnit} overlay /> : null}
        </DragOverlay>
      </DndContext>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', padding: '18px 22px 4px' }}>
        <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving || !dirty}>
          {saving ? <><span className="spinner" /> Saving…</> : <><Icon name="check" size={15} /> Save Order</>}
        </button>
        <button className="btn btn-ghost btn-sm" onClick={handleReset} disabled={saving || !dirty}>
          Reset
        </button>
        {dirty && <span className="small" style={{ color: 'var(--warn)', fontWeight: 600 }}>Unsaved changes</span>}
      </div>
    </div>
  )
}

function GroupColumn({ id, meta, unitIds, unitsById }) {
  const { setNodeRef, isOver } = useDroppable({ id })
  return (
    <div
      ref={setNodeRef}
      style={{
        background: isOver ? 'var(--green-tint)' : 'var(--paper)',
        border: `1px solid ${isOver ? 'var(--fairway)' : 'var(--line)'}`,
        borderRadius: 'var(--r-md)',
        padding: 12,
        minHeight: 90,
        transition: 'background 0.15s var(--ease), border-color 0.15s var(--ease)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 10 }}>
        <span style={{ fontWeight: 700, fontSize: 13, color: 'var(--ink)' }}>Group {meta.group}</span>
        <span className="accent" style={{ fontSize: 13 }}>{meta.teeTime}</span>
      </div>
      <SortableContext items={unitIds} strategy={verticalListSortingStrategy}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 36 }}>
          {unitIds.map(uid => (
            <SortableUnit key={uid} id={uid} unit={unitsById[uid]} />
          ))}
          {unitIds.length === 0 && (
            <div className="small muted" style={{ textAlign: 'center', padding: '8px 0', fontStyle: 'italic' }}>
              Drop players here
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  )
}

function SortableUnit({ id, unit }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id })
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <UnitChip unit={unit} />
    </div>
  )
}

function UnitChip({ unit, overlay }) {
  const isTeam = unit.type === 'team'
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        padding: '8px 10px',
        borderRadius: 'var(--r-sm)',
        cursor: 'grab',
        background: isTeam ? 'var(--champagne-tint)' : '#fff',
        border: `1px solid ${isTeam ? 'var(--champagne)' : 'var(--line)'}`,
        borderLeft: isTeam ? '3px solid var(--champagne-dark)' : '1px solid var(--line)',
        boxShadow: overlay ? 'var(--shadow-lg)' : 'var(--shadow-sm)',
      }}
    >
      <span style={{ color: isTeam ? 'var(--champagne-dark)' : 'var(--faint)', marginTop: 1, flexShrink: 0 }}>
        <Icon name={isTeam ? 'users' : 'flag'} size={15} />
      </span>
      <div style={{ minWidth: 0 }}>
        {isTeam && (
          <div style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--champagne-dark)', marginBottom: 2 }}>
            {unit.teamName}
          </div>
        )}
        {unit.players.map((p, i) => {
          const placeholder = PLACEHOLDER_RE.test(p)
          return (
            <div key={i} style={{ fontSize: 13, color: placeholder ? 'var(--faint)' : 'var(--ink)', fontStyle: placeholder ? 'italic' : 'normal', lineHeight: 1.4 }}>
              {p}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Group a tee schedule into draggable units. Players whose full name maps to a
// team in `teamMap` collapse into one unit per team within their group.
function buildUnits(schedule, teamMap) {
  const unitsById = {}
  const containers = {}
  const meta = {}
  const order = []
  let uid = 0

  for (const g of schedule) {
    const cid = `g${g.group}`
    order.push(cid)
    meta[cid] = { group: g.group, teeTime: g.teeTime }
    containers[cid] = []
    const teamUnitInGroup = {}

    for (const player of g.players) {
      const team = teamMap[player]
      if (team) {
        if (teamUnitInGroup[team] != null) {
          unitsById[teamUnitInGroup[team]].players.push(player)
          continue
        }
        const id = `u${uid++}`
        teamUnitInGroup[team] = id
        unitsById[id] = { id, type: 'team', teamName: team, players: [player] }
        containers[cid].push(id)
      } else {
        const id = `u${uid++}`
        unitsById[id] = { id, type: 'single', players: [player] }
        containers[cid].push(id)
      }
    }
  }
  return { containers, unitsById, meta, order }
}
