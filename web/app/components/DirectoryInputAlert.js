import PropTypes from "prop-types";
import { useState } from "react";
import { XCircleIcon, XMarkIcon } from "@heroicons/react/24/solid";

/**
 * Directory Input Alert component.
 * @param {object} options
 * @param {string} options.root - Directory root path.
 * @param {boolean} options.isVisible=false - Whether to render the component or not.
 * @return {JSX.Element}
 */
function DirectoryInputAlert({ root, isVisible = false }) {
  const [isDismissed, setIsDismissed] = useState(false);

  if (!isVisible) {
    return <></>;
  }

  if (isDismissed) {
    return <></>;
  }

  return (
    <div className="rounded-md bg-red-50 p-4 mt-2">
      <div className="flex">
        <div className="flex-shrink-0">
          <XCircleIcon aria-hidden="true" className="h-5 w-5 text-red-400" />
        </div>
        <div className="ml-3">
          <p className="text-sm font-normal text-red-700">
            Only files in the mounted directory {root} are accessible.
          </p>
        </div>
        <div className="ml-auto pl-3">
          <div className="-mx-1.5 -my-1.5">
            <button
              type="button"
              onClick={() => setIsDismissed(true)}
              className="inline-flex rounded-md bg-red-50 p-1.5 text-red-700 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-600 focus:ring-offset-2 focus:ring-offset-red-50"
            >
              <span className="sr-only">Dismiss</span>
              <XMarkIcon aria-hidden="true" className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

DirectoryInputAlert.propTypes = {
  root: PropTypes.string,
  isVisible: PropTypes.bool,
};

export default DirectoryInputAlert;
