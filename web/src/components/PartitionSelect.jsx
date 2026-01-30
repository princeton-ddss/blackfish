import PropTypes from "prop-types";
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/react";
import { CheckIcon, ChevronUpDownIcon } from "@heroicons/react/20/solid";

function PartitionSelect({ partitions, selectedPartition, setSelectedPartition, disabled }) {
  if (!partitions || partitions.length === 0) {
    return null;
  }

  // Find the selected partition object
  const selected = partitions.find(p => p.name === selectedPartition) || partitions[0];

  return (
    <Listbox
      value={selected}
      onChange={(partition) => setSelectedPartition(partition.name)}
      disabled={disabled}
    >
      <div className="relative">
        <ListboxButton className="relative w-full cursor-default rounded-lg bg-white dark:bg-gray-700 py-2 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 border border-gray-300 dark:border-gray-600 focus:outline-none focus-visible:border-blue-500 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-300 sm:text-sm disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed">
          <span className="block truncate">
            {selected.default ? `${selected.name} (Default)` : selected.name}
          </span>
          <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon
              className="h-5 w-5 text-gray-400"
              aria-hidden="true"
            />
          </span>
        </ListboxButton>
        <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none sm:text-sm">
          {partitions.map((partition) => (
            <ListboxOption
              key={partition.name}
              className={({ active }) =>
                `relative cursor-default select-none py-2 pl-10 pr-4 ${
                  active ? "bg-blue-100 dark:bg-blue-900 text-blue-900 dark:text-blue-100" : "text-gray-900 dark:text-gray-100"
                }`
              }
              value={partition}
            >
              {({ selected: isSelected }) => (
                <>
                  <span
                    className={`block truncate ${
                      isSelected ? "font-medium" : "font-normal"
                    }`}
                  >
                    {partition.default ? `${partition.name} (Default)` : partition.name}
                  </span>
                  {isSelected ? (
                    <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600 dark:text-blue-400">
                      <CheckIcon className="h-5 w-5" aria-hidden="true" />
                    </span>
                  ) : null}
                </>
              )}
            </ListboxOption>
          ))}
        </ListboxOptions>
      </div>
    </Listbox>
  );
}

PartitionSelect.propTypes = {
  partitions: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string.isRequired,
      default: PropTypes.bool,
      tiers: PropTypes.array,
    })
  ),
  selectedPartition: PropTypes.string,
  setSelectedPartition: PropTypes.func.isRequired,
  disabled: PropTypes.bool,
};

export default PartitionSelect;
