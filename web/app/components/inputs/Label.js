"use client";
import PropTypes from "prop-types";

/**
 * Label component.
 * @param {Object} params
 * @param {string} params.label
 * @param {string} params.htmlFor
 * @param {string} params.description
 * @param {boolean} params.disabled
 * @return {JSX.Element}
 */
function Label({ label, htmlFor, description, disabled }) {
  return (
    <label
      htmlFor={htmlFor ?? label}
      className={`relative group inline-flex grow text-sm font-normal leading-6 hover:underline hover:decoration-dotted ${
        disabled ? "text-gray-300" : "text-gray-900"
      }`}
    >
      {label}
      <div className="hidden group-hover:block absolute bottom-6 left-0 lg:-bottom-1 lg:-left-64 w-60 p-2 font-light text-gray-800 text-sm rounded-md bg-white shadow-sm ring-1 ring-inset ring-gray-300 z-10">
        {description}
      </div>
    </label>
  );
}

Label.propTypes = {
  label: PropTypes.string,
  htmlFor: PropTypes.string,
  description: PropTypes.string,
  disabled: PropTypes.bool,
};

export default Label;
