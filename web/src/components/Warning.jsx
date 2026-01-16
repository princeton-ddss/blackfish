import { ExclamationTriangleIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

/**
 * Warning component.
 * @param {object} options
 * @param {string} options.header
 * @param {string} options.message
 * @return {JSX.Element}
 */
function Warning({ header, message }) {
  return (
    <div className="border-l-4 border-yellow-400 bg-yellow-50 p-3">
      <div className="flex">
        <div className="flex-shrink-0">
          <ExclamationTriangleIcon
            className="h-5 w-5 text-yellow-400"
            aria-hidden="true"
          />
        </div>
        <div className="ml-3">
          <div>
            <p className="text-sm text-yellow-700">{header}</p>
          </div>
          <div>
            <p className="font-light text-yellow-700 hover:text-yellow-600">
              {message}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

Warning.propTypes = {
  header: PropTypes.string,
  message: PropTypes.string,
};

export default Warning;
