import type { ReactElement } from 'react'
import { ANSWER_SHAPE, API_BASE_PATH, ENDPOINTS, ITEM_FIELDS, KEY_VARIABLE, curlExample } from '../connect/apiReference'
import { CopyBlock } from '../connect/CopyBlock'
import { Link } from '../route/Link'
import { PATHS } from '../route/useRoute'

/** The API as a reference: the same definition the prompt for a coding agent is written from. */
export function ApiReference(): ReactElement {
  const origin = window.location.origin
  return (
    <>
      <p>
        Every request goes to <code>{`${origin}${API_BASE_PATH}`}</code> with the header{' '}
        <code>{`Authorization: Bearer $${KEY_VARIABLE}`}</code>.{' '}
        <Link to={PATHS.workspace} className="nm-link">
          Get a key in My workspace
        </Link>
        .
      </p>
      <h3>Routes</h3>
      <div className="nm-table-wrap">
        <table className="nm-table">
          <tbody>
            {ENDPOINTS.map((endpoint) => (
              <tr key={`${endpoint.method} ${endpoint.path}`}>
                <th scope="row" className="nm-table__route">
                  <code>
                    <b>{endpoint.method}</b> {endpoint.path}
                  </code>
                </th>
                <td>{endpoint.what}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Fields of a post</h3>
      <div className="nm-table-wrap">
        <table className="nm-table">
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Type</th>
              <th scope="col">Meaning</th>
            </tr>
          </thead>
          <tbody>
            {ITEM_FIELDS.map((field) => (
              <tr key={field.name}>
                <th scope="row" className="nm-table__field">
                  <code>{field.name}</code>
                  {field.required ? <i className="nm-table__required">required</i> : null}
                </th>
                <td>{field.type}</td>
                <td>{field.meaning}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>One post from a terminal</h3>
      <CopyBlock text={curlExample(origin, `$${KEY_VARIABLE}`)} what="the command" />
      <h3>Shape of the answer</h3>
      <pre className="nm-method__shape" tabIndex={0}>
        {ANSWER_SHAPE}
      </pre>
      <p className="nm-note">The dots stand for what the server returns: no value above is a measurement.</p>
    </>
  )
}
