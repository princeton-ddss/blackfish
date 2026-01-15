import React from "react";
import { ExclamationCircleIcon } from "@heroicons/react/24/outline";
import { classNames, randomInt } from "@/app/lib/util";
import PropTypes from "prop-types";


/**
 * Service Modal Validated Input component.
 * @param {object} options
 * @param {string} options.label
 * @param {string} options.help
 * @param {string} options.units
 * @param {string} options.placeholder
 * @param {Function} options.setValue
 * @param {Function} options.validate
 * @param {string} options.value
 * @param {string} options.type
 * @param {boolean} options.disabled
 * @param {string} options.htmlFor
 * @return {JSX.Element}
 */
function ServiceModalValidatedInput({
  label,
  help,
  units,
  placeholder,
  value,
  setValue,
  validate,
  type,
  disabled,
  htmlFor
}) {

  const [isValid, setIsValid] = React.useState(true);
  const [error, setError] = React.useState(null);
  const id = htmlFor ? `${htmlFor}-${randomInt(0, 99)}` : `service-modal-validated-input-${randomInt(0, 99)}`;

  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium leading-6 text-gray-900"
      >
        {label}
      </label>
      {help && <p className="mt-1 text-sm leading-6 text-gray-600">{help}</p>}
      <div className="relative mt-2 rounded-md shadow-sm">
        <input
          id={id}
          type={type}
          disabled={disabled}
          className={classNames(
            !isValid
              ? "text-red-600 ring-red-300 placeholder:text-red-300 focus:ring-red-600"
              : "ring-gray-300 focus:ring-blue-500",
            "block w-full rounded-md border-0 py-1.5 pr-10 ring-inset focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6 disabled:bg-gray-100 disabled:ring-1 disabled:ring-gray-300 ring-1"
          )}
          placeholder={placeholder}
          value={value}
          onChange={(event) => {
            setValue(event.target.value);
            const res = validate(event.target.value);
            if (res.ok) {
              setIsValid(true);
              setError(null);
            } else {
              setIsValid(false);
              setError(res.message);
            }
          }}
          aria-invalid="true"
          aria-describedby="email-error"
        />
        {isValid && (
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3 font-light italic text-sm text-slate-500">
            {units}
          </span>
        )}
        {!isValid && (
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
            <ExclamationCircleIcon
              className="h-5 w-5 text-red-600"
              aria-hidden="true"
            />
          </div>
        )}
      </div>
      {!isValid && (
        <p className="mt-2 text-sm text-red-600" id="email-error">
          {error}
        </p>
      )}
    </div>
  );
}

ServiceModalValidatedInput.propTypes = {
  label: PropTypes.string,
  help: PropTypes.string,
  units: PropTypes.string,
  placeholder: PropTypes.string,
  value: PropTypes.any,
  setValue: PropTypes.func,
  validate: PropTypes.func,
  type: PropTypes.string,
  disabled: PropTypes.bool,
  htmlFor: PropTypes.string,
};

export default ServiceModalValidatedInput;
