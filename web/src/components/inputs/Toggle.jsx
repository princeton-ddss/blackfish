import { Switch, Field } from "@headlessui/react";
import Label from "@/components/inputs/Label";
import PropTypes from "prop-types";
import { classNames } from "@/lib/util";

/**
 * Toggle component.
 * @param {object} options
 * @param {boolean} options.checked
 * @param {Function} options.onChange
 * @param {string} options.label
 * @param {string} options.tooltip
 * @return {JSX.Element}
 */
function Toggle({ checked, onChange, label, tooltip }) {
  const id = "toggle-control";
  return (
    <Field as="div" className="sm:col-span-2">
      <div className="flex flex-row justify-start">
        <Label htmlFor={id} label={label} description={tooltip} />
      </div>
      <Switch
        id={id}
        checked={checked}
        onChange={onChange}
        className={classNames(
          checked ? "bg-blue-500" : "bg-gray-200",
          "mt-1 relative inline-flex h-6 w-11 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        )}
      >
        <span
          aria-hidden="true"
          className={classNames(
            checked ? "translate-x-5" : "translate-x-0",
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out"
          )}
        />
      </Switch>
    </Field>
  );
}

Toggle.propTypes = {
  checked: PropTypes.bool,
  onChange: PropTypes.func,
  label: PropTypes.string,
  tooltip: PropTypes.string,
};

export default Toggle;
