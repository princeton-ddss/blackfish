import PropTypes from "prop-types";

/**
 * A standardized checkbox with label and explanation text.
 * @param {object} options
 * @param {string} options.id - required unique string for `input` and `label` association.
 * @param {boolean} options.checked - the condition determining whether the box is checked.
 * @param {Function} options.onChange - a method to run when the box is clicked.
 * @param {boolean} options.disabled - disabled the `input`.
 * @param {string} options.label - text for the associated `<label>`.
 * @param {string} options.help - extra description text.
 * @return {JSX.Element}
*/
function ServiceModalCheckBox({ id, checked, onChange, disabled, label, help }) {
  return (
    <div className="relative flex gap-x-3">
      <div className="flex h-6 items-center">
        <input
          id={id}
          name={id}
          type="checkbox"
          disabled={disabled}
          checked={checked}
          onChange={onChange}
          className="h-4 w-4 rounded border-gray-300 text-blue-500 focus:ring-blue-500 disabled:bg-gray-100"
        />
      </div>
      <div className="text-sm leading-6">
        <label htmlFor={id} className="font-medium text-gray-900">
          {label}
        </label>
        <p className="text-gray-500">
          {help}
        </p>
      </div>
    </div>
  );
}

ServiceModalCheckBox.propTypes = {
  id: PropTypes.string,
  checked: PropTypes.bool,
  onChange: PropTypes.func,
  disabled: PropTypes.bool,
  label: PropTypes.string,
  help: PropTypes.string,
};

export default ServiceModalCheckBox;
