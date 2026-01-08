import { useState } from "react";
import { XMarkIcon } from "@heroicons/react/24/outline";
import Label from "@/app/components/inputs/Label";
import PropTypes from "prop-types";

const Actions = {
  ADD: "add",
  REMOVE: "remove",
};

/**
 * Chips component.
 * @param {object} options
 * @param {Array.<string>} options.values
 * @param {Function} options.onChange
 * @param {string} options.label
 * @param {string} options.tooltip
 * @return {JSX.Element}
 */
function Chips({ values, onChange, label, tooltip }) {
  const [input, setInput] = useState("");
  const id = "chips-control";

  const handleAdd = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      const success = onChange(input, Actions.ADD);
      if (success) {
        setInput("");
      }
    }
  };

  const handleRemove = (index) => {
    onChange(index, Actions.REMOVE);
  };

  return (
    <div className="sm:col-span-4">
      <div className="flex flex-row justify-start">
        <Label htmlFor={id} label={label} description={tooltip} />
      </div>

      <input
        id={id}
        type="text"
        value={input}
        onChange={(event) => setInput(event.target.value)}
        onKeyDown={(event) => handleAdd(event)}
        className={`mt-1 block w-full border-1 border-gray-300 rounded-md shadow-sm py-1 px-2 focus:border-white focus:ring-2 focus:ring-blue-500 sm:text-sm`}
      />

      <div className="mt-1.5 flex flex-wrap gap-1">
        {values.map((val, index) => (
          <div
            key={`${val}-${index}`}
            className="flex items-center bg-blue-500 text-white font-extralight sm:text-sm pl-3 pr-2 py-1 rounded-full"
          >
            <span>{val}</span>
            <button
              id={`remove-button-${index}`}
              type="button"
              onClick={() => handleRemove(index)}
              className="ml-1 text-white font-light hover:text-blue-200"
            >
              <XMarkIcon className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

Chips.propTypes = {
  values: PropTypes.array,
  onChange: PropTypes.func,
  label: PropTypes.string,
  tooltip: PropTypes.string,
};

export default Chips;
