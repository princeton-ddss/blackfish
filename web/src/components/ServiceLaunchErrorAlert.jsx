import { XCircleIcon, XMarkIcon } from '@heroicons/react/20/solid'
import PropTypes from "prop-types";

/**
 * Service Launch Error Alert component.
 * @param {object} options
 * @param {object} options.error
 * @param {string} options.error.message
 * @param {Function} options.onClick
 * @return {JSX.Element}
 */
function ServiceLaunchErrorAlert({error, onClick}) {
  return (
    <div className="rounded-md bg-red-50 p-4 mb-4">
      <div className="flex">
        <div className="shrink-0">
          <XCircleIcon aria-hidden="true" className="h-5 w-5 text-red-400" />
        </div>
        <div className="ml-3">
          <h3 className="text-sm font-medium text-red-800">Failed to launch service.</h3>
          <div className="mt-2 text-sm text-red-700">
            <ul role="list" className="list-disc space-y-1 pl-5">
              <li>{error.message}</li>
            </ul>
          </div>
        </div>
        <div className="ml-auto pl-3">
          <div className="-mx-1.5 -my-1.5">
            <button
              type="button"
              onClick={onClick}
              className="inline-flex rounded-md bg-red-50 p-1.5 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
            >
              <span className="sr-only">Dismiss</span>
              <XMarkIcon aria-hidden="true" className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

ServiceLaunchErrorAlert.propTypes = {
  error: PropTypes.object,
  onClick: PropTypes.func,
};

export default ServiceLaunchErrorAlert;
