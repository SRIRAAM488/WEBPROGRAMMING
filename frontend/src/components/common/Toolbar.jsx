/** Toolbar - a shared search + filter bar used by the list pages. */

import { Search, X } from 'lucide-react'

export default function Toolbar({ search, onSearchChange, searchPlaceholder = 'Search…', children }) {
  return (
    <div className="toolbar">
      <div className="search-box">
        <Search size={16} aria-hidden="true" />
        <input
          type="search"
          className="input"
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          aria-label={searchPlaceholder}
        />
        {search ? (
          <button
            type="button"
            className="search-box__clear"
            onClick={() => onSearchChange('')}
            aria-label="Clear search"
          >
            <X size={13} />
          </button>
        ) : null}
      </div>

      {children}
    </div>
  )
}

/** A labelled <select> for filters. */
export function FilterSelect({ label, value, onChange, options, allLabel = 'All' }) {
  return (
    <select
      className="select toolbar__select"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      aria-label={label}
    >
      <option value="all">{allLabel}</option>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}

/** A pill-style filter, easier to tap on mobile than a select. */
export function FilterChips({ options, value, onChange, counts }) {
  return (
    <div className="chips" role="group" aria-label="Filter">
      {options.map((option) => {
        const active = value === option.value
        return (
          <button
            key={option.value}
            type="button"
            className={`chip${active ? ' chip--active' : ''}`}
            onClick={() => onChange(option.value)}
            aria-pressed={active}
          >
            {option.label}
            {counts && counts[option.value] !== undefined ? (
              <span className="chip__count">{counts[option.value]}</span>
            ) : null}
          </button>
        )
      })}
    </div>
  )
}