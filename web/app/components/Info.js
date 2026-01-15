import { InformationCircleIcon } from "@heroicons/react/20/solid";
import PropTypes from "prop-types";

/**
 * Info component.
 * @param {object} options
 * @param {string} options.header
 * @param {string} options.message
 * @return {JSX.Element}
 */
function Info({ header, message }) {
  return (
    <div className="border-l-4 border-blue-400 bg-blue-50 p-4">
      <div className="flex">
        <div className="flex-shrink-0">
          <InformationCircleIcon
            className="h-5 w-5 text-blue-400"
            aria-hidden="true"
          />
        </div>
        <div className="ml-3">
          <div className="text-sm text-blue-600">
            { header + " "}
            <div
              className="font-light text-blue-600 hover:text-blue-500"
            >
              { message }
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Info.propTypes = {
  header: PropTypes.string,
  message: PropTypes.string,
};

export default Info;
