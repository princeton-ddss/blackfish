import ServiceModalCheckbox from "@/app/components/ServiceModalCheckbox"
import PropTypes from "prop-types";

function TextGenerationContainerOptionsForm({
  containerOptions,
  setContainerOptions,
  disabled
}) {
  return (
    <>
      <fieldset>
        <legend className="text-sm font-semibold leading-6 text-gray-900">
          Deployment
        </legend>
        <p className="mt-1 mb-2 text-sm leading-6 text-gray-600">
          Customize the service deployment.
        </p>
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
