import { useState } from "react";
import { ChevronDownIcon, ChevronUpIcon } from "@heroicons/react/20/solid";
import ServiceModalCheckbox from "@/components/ServiceModalCheckbox"
import { useScrollOnExpand } from "@/lib/useScrollOnExpand";
import PropTypes from "prop-types";

function TextGenerationContainerOptionsForm({
  containerOptions,
  setContainerOptions,
  disabled
}) {
  const [expanded, setExpanded] = useState(false);
  // This section sits at the bottom of the modal, so expanding it without
  // scrolling reveals nothing until the user scrolls down themselves.
  useScrollOnExpand(expanded);

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
          <div className="mt-3 space-y-3">
            <ServiceModalCheckbox
              checked={containerOptions.disable_thinking}
              onChange={() => setContainerOptions(prevContainerOptions => {
                return {
                  ...prevContainerOptions,
                  disable_thinking: !prevContainerOptions.disable_thinking,
                };
              })}
              label="Disable Thinking"
              help="Disables thinking/reasoning output for models that support it."
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
