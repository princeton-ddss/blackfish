import PropTypes from "prop-types";
import { XCircleIcon } from "@heroicons/react/24/solid";

/**
 * Directory Input Alert component. Transient feedback shown while a rejected
 * (out-of-mount) path is pending; it clears on its own once a valid path is
 * entered, so it has no manual dismiss.
 * @param {object} options
 * @param {string} options.root - Directory root path.
 * @param {boolean} options.isVisible=false - Whether to render the component or not.
 * @return {JSX.Element}
 */
function DirectoryInputAlert({ root, isVisible = false }) {
  if (!isVisible) {
    return <></>;
  }

  return (
    <div className="rounded-md bg-red-50 dark:bg-red-950 p-4 mt-2">
      <div className="flex">
        <div className="flex-shrink-0">
          <XCircleIcon aria-hidden="true" className="h-5 w-5 text-red-400" />
        </div>
        <div className="ml-3">
          <p className="text-sm font-normal text-red-700 dark:text-red-300">
            Only files in the mounted directory {root} are accessible.
          </p>
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
