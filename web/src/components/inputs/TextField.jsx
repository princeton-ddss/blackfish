import Label from "@/components/inputs/Label";
import PropTypes from "prop-types";

/**
 * Text field component.
 * @param {object} options
 * @param {string} options.label
 * @param {string} options.tooltip
 * @param {string} options.value
 * @param {Function} options.onChange
 * @param {string} options.placeholder
 * @param {boolean} options.disabled
 * @param {string} options.error
 * @return {JSX.Element}
 */
function TextField({
  label,
  tooltip,
  value,
  onChange,
  placeholder,
  disabled,
  error,
}) {
  return (
    <div className="sm:col-span-4">
      <div className="flex flex-row justify-start">
        <Label
          label={label}
          description={tooltip}
          disabled={disabled}
        />
      </div>
      <input
        type="text"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        disabled={disabled}
        onKeyDown={(event) => {
          // Only allow digits and editing (Backspace, Enter, Meta-a, Esc, Tab)
          const allowedKeys = ["Backspace", "Enter", "Esc", "Tab"];
          if (event.metaKey && event.key === "a") {
            return;
          } else if (allowedKeys.includes(event.key)) {
            return;
          } else if (!isNaN(Number(event.key))) {
            return;
          } else {
            event.preventDefault();
          }
        }}
        className={`mt-1 block w-full border ${
          error
            ? "border-red-500"
            : disabled
            ? "border-gray-100 dark:border-gray-700"
            : "border-gray-300 dark:border-gray-600"
        } bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md shadow-sm px-2 py-1 focus:border-white dark:focus:border-gray-500 focus:ring-2 focus:ring-blue-500 sm:text-sm`}
      />
      {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
    </div>
  );
}

TextField.propTypes = {
  label: PropTypes.string,
  tooltip: PropTypes.string,
  value: PropTypes.string,
  onChange: PropTypes.func,
  placeholder: PropTypes.string,
  disabled: PropTypes.bool,
  error: PropTypes.string,
};

export default TextField;
