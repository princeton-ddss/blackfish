import { Field, Label } from "@headlessui/react";
import PropTypes from "prop-types";

/**
 * Loading skeleton for select controls.
 * @param {object} options
 * @param {string} options.label
 * @return {JSX.Element}
 */
function SelectSkeleton({ label }) {
  return (
    <Field disabled>
      <Label className="block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100">
        {label}
      </Label>
      <div className="relative mt-2">
        <div
          aria-label={`${label} loading`}
          aria-busy="true"
          className="h-9 w-full animate-pulse rounded-md bg-gray-200 dark:bg-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600"
        />
      </div>
    </Field>
  );
}

SelectSkeleton.propTypes = {
  label: PropTypes.string.isRequired,
};

export default SelectSkeleton;
