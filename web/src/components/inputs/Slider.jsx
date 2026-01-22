import { ArrowUturnLeftIcon } from "@heroicons/react/24/solid";
import Label from "./Label";
import PropTypes from "prop-types";
import { classNames } from "@/lib/util";


/**
 * Slider component.
 * @param {object} options
 * @param {string} options.name
 * @param {number} options.value
 * @param {Function} options.onSliderChange
 * @param {Function} options.onTextChange
 * @param {Function} options.onReset
 * @param {number} options.min
 * @param {number} options.max
 * @param {number} options.step
 * @param {string} options.tooltip
 * @param {boolean} options.disabled
 * @param {boolean} options.optional
 * @param {boolean} options.enabled
 * @param {Function} options.onOptionalToggle
 * @return {JSX.Element}
 */
function Slider({
  name,
  value,
  onSliderChange,
  onTextChange,
  onReset,
  min,
  max,
  step,
  tooltip,
  disabled,
  optional,
  enabled,
  onOptionalToggle,
}) {
  const isDisabled = disabled || (optional && !enabled);
  const id = name.toLowerCase().replaceAll(" ", "-");

  return (
    <div className="sm:col-span-4">
      <div className="flex flex-row justify-between items-center">
        {/* Left: Label and optional checkbox */}
        <div className="flex items-center space-x-1">
          {optional && (
            <input
              type="checkbox"
              checked={enabled}
              onChange={() => onOptionalToggle?.(!enabled)}
              className="mr-1 ml-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
          )}
          <Label htmlFor={id} label={name} description={tooltip} disabled={isDisabled} />
        </div>

        {/* Right: Reset button and number input */}
        <div className="flex items-center space-x-2">
          <button
            onClick={onReset}
            disabled={isDisabled}
            className={classNames(
              "mr-0.5",
              isDisabled ? "cursor-not-allowed opacity-40" : ""
            )}
          >
            <ArrowUturnLeftIcon className="h-3 w-3 text-gray-500" />
          </button>
          <input
            type="number"
            step={step ?? 1}
            value={value}
            onKeyDown={(event) => {
              if (event.key === "Enter") event.preventDefault();
            }}
            onChange={onTextChange}
            disabled={isDisabled}
            className="block w-20 border border-gray-300 rounded-md shadow-sm h-7 text-right sm:text-sm font-light text-gray-900 focus:ring-inset focus:ring-2 focus:ring-blue-500 focus:border-white"
          />
        </div>
      </div>

      {/* Slider input */}
      <div className="mt-0">
        <div className="flex sm:max-w-md">
          <input
            type="range"
            name={id}
            id={id}
            min={min}
            max={max}
            step={step ?? 1}
            value={value}
            onChange={onSliderChange}
            disabled={isDisabled}
            className="block flex-1 border-0 bg-transparent py-1.5 pl-1 text-gray-900 placeholder:text-gray-400 focus:ring-0 sm:text-sm sm:leading-6"
          />
        </div>
      </div>
    </div>
  );
}

Slider.propTypes = {
  name: PropTypes.string,
  value: PropTypes.number,
  onSliderChange: PropTypes.func,
  onTextChange: PropTypes.func,
  onReset: PropTypes.func,
  min: PropTypes.number,
  max: PropTypes.number,
  step: PropTypes.number,
  tooltip: PropTypes.string,
  disabled: PropTypes.bool,
  optional: PropTypes.bool,
  enabled: PropTypes.bool,
  onOptionalToggle: PropTypes.func,
};

export default Slider;
