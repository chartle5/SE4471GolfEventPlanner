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
  }

  function handleDragOver(event) {
    const { active, over } = event
    if (!over) return
    const activeContainer = findContainer(active.id)
    const overContainer = findContainer(over.id) || (over.id in containers ? over.id : null)
    if (!activeContainer || !overContainer || activeContainer === overContainer) return

    setContainers(prev => {
      const activeItems = prev[activeContainer]
      const overItems = prev[overContainer]
      const activeIndex = activeItems.indexOf(active.id)
      let newIndex = overItems.indexOf(over.id)
      if (newIndex === -1) newIndex = overItems.length
      return {
        ...prev,
        [activeContainer]: activeItems.filter(id => id !== active.id),
        [overContainer]: [
          ...overItems.slice(0, newIndex),
          active.id,
          ...overItems.slice(newIndex),
        ],
      }
    })
    setDirty(true)
  }

  function handleDragEnd(event) {
    const { active, over } = event
    setActiveId(null)
    if (!over) return
    const activeContainer = findContainer(active.id)
    const overContainer = findContainer(over.id) || (over.id in containers ? over.id : null)
    if (!activeContainer || !overContainer) return

    if (activeContainer === overContainer) {
      const items = containers[activeContainer]
      const oldIndex = items.indexOf(active.id)
      const newIndex = items.indexOf(over.id)
      if (oldIndex !== newIndex && newIndex !== -1) {
        setContainers(prev => ({ ...prev, [activeContainer]: arrayMove(items, oldIndex, newIndex) }))
        setDirty(true)
      }
    }
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
          Drag players between tee groups to rearrange pairings. Teammates are
          locked together (gold blocks) and always move as one.
        </span>
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragOver={handleDragOver}
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
