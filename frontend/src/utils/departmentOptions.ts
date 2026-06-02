interface DepartmentLike {
  id: number
  name: string
  parent_id: number | null
  order_no: number
}

export type DepartmentSelectOption<T extends DepartmentLike> = T & {
  plain_name: string
  depth: number
}

function sortDepartments<T extends DepartmentLike>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    if (a.order_no !== b.order_no) {
      return a.order_no - b.order_no
    }
    return a.name.localeCompare(b.name, 'vi')
  })
}

export function toDepartmentSelectOptions<T extends DepartmentLike>(
  departments: T[],
): DepartmentSelectOption<T>[] {
  const byParent = new Map<number | null, T[]>()

  for (const department of departments) {
    const parentKey = department.parent_id ?? null
    const siblings = byParent.get(parentKey) ?? []
    siblings.push(department)
    byParent.set(parentKey, siblings)
  }

  const visited = new Set<number>()
  const flattened: DepartmentSelectOption<T>[] = []

  const walk = (parentId: number | null, depth: number) => {
    const siblings = sortDepartments(byParent.get(parentId) ?? [])
    for (const department of siblings) {
      if (visited.has(department.id)) continue
      visited.add(department.id)
      const plainName = department.name
      const indentedName = depth === 0
        ? plainName
        : `${'-- '.repeat(depth)}${plainName}`
      flattened.push({
        ...department,
        plain_name: plainName,
        name: indentedName,
        depth,
      })
      walk(department.id, depth + 1)
    }
  }

  walk(null, 0)

  const orphans = sortDepartments(
    departments.filter((department) => !visited.has(department.id)),
  )
  for (const department of orphans) {
    flattened.push({
      ...department,
      plain_name: department.name,
      name: department.name,
      depth: 0,
    })
  }

  return flattened
}

export function toDepartmentOptionItems<T extends DepartmentLike>(
  departments: T[],
): Array<{ label: string; value: number }> {
  return toDepartmentSelectOptions(departments).map((department) => ({
    label: department.name,
    value: department.id,
  }))
}
