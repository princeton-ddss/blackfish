import { useState } from "react";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/20/solid";
import ServiceModalCheckbox from "@/components/ServiceModalCheckbox"
import PropTypes from "prop-types";

function TextGenerationContainerOptionsForm({
  containerOptions,
  setContainerOptions,
  disabled
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <fieldset>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 w-full text-left"
        >
          <legend className="text-sm font-semibold leading-6 text-gray-900 dark:text-gray-100">
            Deployment Options
          </legend>
          {expanded ? (
            <ChevronUpIcon className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDownIcon className="h-4 w-4 text-gray-500" />
          )}
        </button>
        {expanded && (
          <div className="mt-3">
            <ServiceModalCheckbox
              checked={containerOptions.disable_custom_kernels}
              onChange={() => setContainerOptions(prevContainerOptions => {
                return {
                  ...prevContainerOptions,
                  disable_custom_kernels: !prevContainerOptions.disable_custom_kernels,
                };
              })}
              label="Disable Custom Kernels"
              help="Disables custom CUDA kernels that may not work on all devices."
              disabled={disabled}
            />
          </div>
        )}
      </fieldset>
    </>
  )
}

TextGenerationContainerOptionsForm.propTypes = {
  containerOptions: PropTypes.object,
  setContainerOptions: PropTypes.func,
  disabled: PropTypes.bool,
};

export default TextGenerationContainerOptionsForm;
