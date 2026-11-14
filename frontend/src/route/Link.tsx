import type { AnchorHTMLAttributes, ReactElement } from 'react'
import { navigate } from './useRoute'

interface LinkProps extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href'> {
  /** A path of the app, with an optional `#section`. */
  to: string
}

/** A link to a page of the app: a real anchor (open in a new tab works), followed in place. */
export function Link({ to, onClick, children, ...rest }: LinkProps): ReactElement {
  return (
    <a
      {...rest}
      href={to}
      onClick={(event) => {
        onClick?.(event)
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
        event.preventDefault()
        navigate(to)
      }}
    >
      {children}
    </a>
  )
}
