import PropTypes from "prop-types";

/**
 * Model Summary component.
 * @param {object} options
 * @param {object} options.model
 * @param {string} options.model.description
 * @param {string} options.model.link
 * @param {Function} options.setModalOpen
 * @return {JSX.Element}
 */
function ModelSummary({
  model,
  setModalOpen,
}) {
  return (
    <div className=" flex flex-row justify-start border-b">
      <div className="grow flex flex-col justify-center mt-2 mb-6">
        <div className="mt-2 ml-1 font-light text-sm sm:flex sm:flex-col">
          <div className="mb-1 ml-0 flex flex-col justify-start items-left">
            <div className="inline-flex items-center mb-2">
              {/* <InformationCircleIcon className="h-6 w-6 text-gray-400 mr-1" /> */}
              <div className="grow font-medium text-sm mr-1">Description </div>
            </div>
            {model?.description}
          </div>

          <div className="mt-2 mb-1 ml-0 flex flex-col justify-start items-left">
            <div className="inline-flex items-center mb-2">
              {/* <LinkIcon className="h-6 w-6 text-gray-400 mr-1" /> */}
              <div className="grow font-medium text-sm mr-1">Link </div>
            </div>
            <a href={model?.link}>{model?.link}</a>
          </div>

          {/* <div className="mt-2 mb-1 flex flex-row justify-end">
            <div className="inline-flex items-center mb-2">
              <LinkIcon className="h-6 w-6 text-gray-400 mr-1" />
              <a
                className="font-medium text-sm mr-1 hover:text-gray-500"
                href={link}
              >
                Link
              </a>
            </div>
          </div> */}
        </div>
        <div>
          <button
            type="button"
            className="mt-2 w-full flex flex-row justify-center gap-x-2 rounded-md bg-tranparent px-3.5 py-1.5 text-sm font-regular shadow-sm hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 border"
            onClick={() => {
              setModalOpen(true);
            }}
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}

ModelSummary.propTypes = {
  model: PropTypes.object,
  setModalOpen: PropTypes.func,
};

export default ModelSummary;
