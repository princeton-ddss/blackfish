import ServiceModalValidatedInput from "@/app/components/ServiceModalValidatedInput"
import PropTypes from "prop-types";


function SpeechRecognitionContainerOptionsForm({
  containerOptions,
  setContainerOptions,
  setValidationErrors,
  disabled
}) {

  function validate(inputDir) {
    if (!inputDir || inputDir.trim() === "") {
      const error = {
        message: "Input directory is required.",
        ok: false,
      };
      setValidationErrors((prevValidationErrors) => {
        return {
          ...prevValidationErrors,
          input_dir: error,
        };
      });
      return error;
    }

    setValidationErrors((prevValidationErrors) => {
      return {
        ...prevValidationErrors,
        input_dir: null,
      }
    })
    return { ok: true };
  }

  return (
    <>
      <fieldset>

        <ServiceModalValidatedInput
          label="Input Directory"
          help="Select a directory containing audio files."
          value={containerOptions.input_dir}
          setValue={(value) => {
            setContainerOptions((prevContainerOptions) => {
              return {
                ...prevContainerOptions,
                input_dir: value,
              }
            })
          }}
          validate={validate}
          type="text"
          disabled={disabled}
        />

      </fieldset>
    </>
  )
}

SpeechRecognitionContainerOptionsForm.propTypes = {
  containerOptions: PropTypes.object,
  setContainerOptions: PropTypes.func,
  setValidationErrors: PropTypes.func,
  disabled: PropTypes.bool,
};

export default SpeechRecognitionContainerOptionsForm;
