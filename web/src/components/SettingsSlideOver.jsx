import { useState, useEffect, useContext, createContext, Fragment } from "react";
import PropTypes from "prop-types";
import {
  Dialog,
  DialogBackdrop,
  DialogPanel,
  DialogTitle,
  TransitionChild,
  Listbox,
  ListboxButton,
  ListboxOption,
  ListboxOptions,
  Label,
  Transition,
} from "@headlessui/react";
import {
  XMarkIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
  PencilIcon,
  TrashIcon,
  CheckIcon,
  ChevronUpDownIcon,
} from "@heroicons/react/24/outline";
import { useSettings } from "@/providers/SettingsProvider";
import { useTheme } from "@/providers/ThemeProvider";
import { ProfileContext } from "@/components/ProfileSelect";
import { useProfiles } from "@/lib/loaders";
import Notification from "@/components/Notification";
import { createProfile, updateProfile, deleteProfile, fetchHfTokenStatus, setHfToken, deleteHfToken, fetchAppInfo } from "@/lib/requests";
import { blackfishApiURL } from "@/config";

// Context for toast notifications within Settings
const NotificationContext = createContext({ showError: () => {}, showSuccess: () => {} });
const useNotification = () => useContext(NotificationContext);

// Theme selector tabs
const themeOptions = [
  { id: "light", name: "Light", icon: SunIcon },
  { id: "dark", name: "Dark", icon: MoonIcon },
  { id: "system", name: "System", icon: ComputerDesktopIcon },
];

function ThemeSelector() {
  const { theme, setTheme } = useTheme();

  return (
    <div className="flex justify-center">
      <div className="inline-flex rounded-md shadow-sm">
        {themeOptions.map((option, index) => {
          const Icon = option.icon;
          const isSelected = theme === option.id;
          const isFirst = index === 0;
          const isLast = index === themeOptions.length - 1;
          return (
            <button
              key={option.id}
              onClick={() => setTheme(option.id)}
              className={`flex items-center justify-center gap-1 px-2.5 py-1 text-xs font-medium transition-colors border ${
                isFirst ? "rounded-l-md" : ""
              } ${isLast ? "rounded-r-md" : ""} ${!isFirst ? "-ml-px" : ""} ${
                isSelected
                  ? "bg-blue-500 text-white border-blue-500 z-10"
                  : "bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span>{option.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

const schemaTypes = [
  { id: "local", name: "Local" },
  { id: "slurm", name: "Slurm" },
];

function ProfileForm({ profile, onSave, onCancel }) {
  const isNew = !profile;
  const [formData, setFormData] = useState({
    name: profile?.name || "",
    schema_type: profile?.schema || "local",
    home_dir: profile?.home_dir || "",
    cache_dir: profile?.cache_dir || "",
    host: profile?.host || "",
    user: profile?.user || "",
    python_path: profile?.python_path || "",
  });
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const selectedType = schemaTypes.find((t) => t.id === formData.schema_type) || schemaTypes[0];

  const validateForm = () => {
    const errors = {};

    // Required fields
    if (!formData.name.trim()) errors.name = "Name is required";
    if (!formData.home_dir.trim()) errors.home_dir = "Home directory is required";
    if (!formData.cache_dir.trim()) errors.cache_dir = "Cache directory is required";

    // Directory format (should start with / or ~)
    if (formData.home_dir && !/^[~/]/.test(formData.home_dir)) {
      errors.home_dir = "Should be an absolute path (start with / or ~)";
    }
    if (formData.cache_dir && !/^[~/]/.test(formData.cache_dir)) {
      errors.cache_dir = "Should be an absolute path (start with / or ~)";
    }

    // Slurm-specific validation
    if (formData.schema_type === "slurm") {
      if (!formData.host.trim()) errors.host = "Host is required";
      if (!formData.user.trim()) errors.user = "User is required";

      // Basic hostname validation (alphanumeric, dots, hyphens)
      if (formData.host && !/^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/.test(formData.host)) {
        errors.host = "Invalid hostname format";
      }
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) return;

    setSaving(true);

    try {
      const data = {
        name: formData.name,
        schema_type: formData.schema_type,
        home_dir: formData.home_dir,
        cache_dir: formData.cache_dir,
      };

      if (formData.schema_type === "slurm") {
        data.host = formData.host;
        data.user = formData.user;
        if (formData.python_path) data.python_path = formData.python_path;
      }

      if (isNew) {
        await createProfile(data);
      } else {
        await updateProfile(profile.name, data);
      }
      onSave();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const inputClasses = (hasError) => `block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm ring-1 ring-inset ${hasError ? "ring-red-500 dark:ring-red-500" : "ring-gray-300 dark:ring-gray-600"} focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed`;
  const labelClasses = "block text-sm font-medium leading-6 text-gray-900 dark:text-gray-100";
  const errorClasses = "mt-1 text-xs text-red-600 dark:text-red-400";

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && (
        <div className="rounded-md bg-red-50 dark:bg-red-900/20 p-2 text-sm text-red-700 dark:text-red-400">
          {error}
        </div>
      )}

      {/* Name */}
      <div>
        <label className={labelClasses}>Name</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          disabled={!isNew}
          className={`mt-1 ${inputClasses(fieldErrors.name)}`}
        />
        {fieldErrors.name && <p className={errorClasses}>{fieldErrors.name}</p>}
      </div>

      {/* Type */}
      <div>
        <Listbox value={selectedType} onChange={(type) => setFormData({ ...formData, schema_type: type.id })}>
          {({ open }) => (
            <>
              <Label className={labelClasses}>Type</Label>
              <div className="relative mt-1">
                <ListboxButton className="relative w-full cursor-default rounded-md bg-white dark:bg-gray-700 py-1.5 pl-3 pr-10 text-left text-gray-900 dark:text-gray-100 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:text-sm sm:leading-6">
                  <span className="block truncate">{selectedType.name}</span>
                  <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
                    <ChevronUpDownIcon className="h-5 w-5 text-gray-400" aria-hidden="true" />
                  </span>
                </ListboxButton>
                <Transition
                  show={open}
                  as={Fragment}
                  leave="transition ease-in duration-100"
                  leaveFrom="opacity-100"
                  leaveTo="opacity-0"
                >
                  <ListboxOptions className="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white dark:bg-gray-700 py-1 text-base shadow-lg ring-1 ring-black dark:ring-gray-600 ring-opacity-5 focus:outline-none sm:text-sm">
                    {schemaTypes.map((type) => (
                      <ListboxOption
                        key={type.id}
                        value={type}
                        className={({ focus }) =>
                          `relative cursor-default select-none py-2 pl-3 pr-9 ${
                            focus ? "bg-blue-500 text-white" : "text-gray-900 dark:text-gray-100"
                          }`
                        }
                      >
                        {({ selected, focus }) => (
                          <>
                            <span className={`block truncate ${selected ? "font-semibold" : "font-normal"}`}>
                              {type.name}
                            </span>
                            {selected && (
                              <span className={`absolute inset-y-0 right-0 flex items-center pr-4 ${focus ? "text-white" : "text-blue-600"}`}>
                                <CheckIcon className="h-5 w-5" aria-hidden="true" />
                              </span>
                            )}
                          </>
                        )}
                      </ListboxOption>
                    ))}
                  </ListboxOptions>
                </Transition>
              </div>
            </>
          )}
        </Listbox>
      </div>

      {/* Host (slurm only) */}
      {formData.schema_type === "slurm" && (
        <div>
          <label className={labelClasses}>Host</label>
          <input
            type="text"
            value={formData.host}
            onChange={(e) => setFormData({ ...formData, host: e.target.value })}
            placeholder="cluster.example.edu"
            className={`mt-1 ${inputClasses(fieldErrors.host)}`}
          />
          {fieldErrors.host && <p className={errorClasses}>{fieldErrors.host}</p>}
        </div>
      )}

      {/* User (slurm only) */}
      {formData.schema_type === "slurm" && (
        <div>
          <label className={labelClasses}>User</label>
          <input
            type="text"
            value={formData.user}
            onChange={(e) => setFormData({ ...formData, user: e.target.value })}
            className={`mt-1 ${inputClasses(fieldErrors.user)}`}
          />
          {fieldErrors.user && <p className={errorClasses}>{fieldErrors.user}</p>}
        </div>
      )}

      {/* Home Directory */}
      <div>
        <label className={labelClasses}>Home Directory</label>
        <input
          type="text"
          value={formData.home_dir}
          onChange={(e) => setFormData({ ...formData, home_dir: e.target.value })}
          placeholder="~/.blackfish"
          className={`mt-1 ${inputClasses(fieldErrors.home_dir)}`}
        />
        {fieldErrors.home_dir && <p className={errorClasses}>{fieldErrors.home_dir}</p>}
      </div>

      {/* Cache Directory */}
      <div>
        <label className={labelClasses}>Cache Directory</label>
        <input
          type="text"
          value={formData.cache_dir}
          onChange={(e) => setFormData({ ...formData, cache_dir: e.target.value })}
          placeholder="~/.cache/huggingface/hub"
          className={`mt-1 ${inputClasses(fieldErrors.cache_dir)}`}
        />
        {fieldErrors.cache_dir && <p className={errorClasses}>{fieldErrors.cache_dir}</p>}
      </div>

      {/* Python Path (slurm only, optional) */}
      {formData.schema_type === "slurm" && (
        <div>
          <label className={labelClasses}>
            Python Path <span className="text-xs font-normal text-gray-500 dark:text-gray-400">Optional</span>
          </label>
          <input
            type="text"
            value={formData.python_path}
            onChange={(e) => setFormData({ ...formData, python_path: e.target.value })}
            placeholder="/usr/bin/python3"
            className={`mt-1 ${inputClasses(false)}`}
          />
        </div>
      )}

      <div className="flex justify-end gap-3 pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-blue-500 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-blue-600 disabled:opacity-50"
        >
          {saving ? "Saving..." : isNew ? "Create" : "Save"}
        </button>
      </div>
    </form>
  );
}

ProfileForm.propTypes = {
  profile: PropTypes.shape({
    name: PropTypes.string,
    schema: PropTypes.string,
    home_dir: PropTypes.string,
    cache_dir: PropTypes.string,
    host: PropTypes.string,
    user: PropTypes.string,
    python_path: PropTypes.string,
  }),
  onSave: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
};

function ProfilesSkeleton() {
  return (
    <div className="divide-y divide-gray-100 dark:divide-gray-700">
      {[1, 2].map((i) => (
        <div key={i} className="py-3 first:pt-0 last:pb-0 animate-pulse">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="h-4 w-20 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-5 w-12 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
            <div className="flex items-center gap-1">
              <div className="h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="h-8 w-8 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          </div>
          <div className="mt-1.5 h-3 w-24 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      ))}
    </div>
  );
}

function ProfilesSection() {
  const { profiles, mutate, isLoading } = useProfiles();
  const { profile: selectedProfile, setProfile } = useContext(ProfileContext);
  const { showError, showSuccess } = useNotification();
  const [editingProfile, setEditingProfile] = useState(null);
  const [isAdding, setIsAdding] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  const handleDelete = async (profileName) => {
    try {
      await deleteProfile(profileName);
      // If we deleted the selected profile, clear selection
      if (selectedProfile?.name === profileName) {
        setProfile(null);
      }
      mutate();
      setDeleteConfirm(null);
      showSuccess(`Profile "${profileName}" deleted`);
    } catch (err) {
      showError(err.message);
    }
  };

  const handleSave = () => {
    mutate();
    setEditingProfile(null);
    setIsAdding(false);
  };

  const renderHeader = () => (
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
        Profiles
      </h3>
      {!isAdding && !editingProfile && (
        <button
          onClick={() => setIsAdding(true)}
          className="rounded-md bg-blue-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600"
        >
          Add Profile
        </button>
      )}
    </div>
  );

  if (isLoading) {
    return (
      <div>
        {renderHeader()}
        <ProfilesSkeleton />
      </div>
    );
  }

  if (isAdding) {
    return (
      <div>
        {renderHeader()}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <ProfileForm onSave={handleSave} onCancel={() => setIsAdding(false)} />
        </div>
      </div>
    );
  }

  if (editingProfile) {
    return (
      <div>
        {renderHeader()}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4">
          <ProfileForm profile={editingProfile} onSave={handleSave} onCancel={() => setEditingProfile(null)} />
        </div>
      </div>
    );
  }

  return (
    <div>
      {renderHeader()}
      <div className="divide-y divide-gray-100 dark:divide-gray-700 mt-2">
        {profiles?.map((p) => (
          <div key={p.name} className="py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {selectedProfile?.name === p.name && (
                  <CheckIcon className="h-4 w-4 text-blue-500" />
                )}
                <span className="text-sm font-medium text-gray-900 dark:text-white">{p.name}</span>
                <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium ${
                  p.schema === "slurm"
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                }`}>
                  {p.schema}
                </span>
              </div>
              <div className="flex items-center gap-1">
                {deleteConfirm === p.name ? (
                  <>
                    <button
                      onClick={() => setDeleteConfirm(null)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                      title="Cancel"
                    >
                      <XMarkIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => handleDelete(p.name)}
                      className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                    >
                      Delete
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => setEditingProfile(p)}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                      title="Edit"
                    >
                      <PencilIcon className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(p.name)}
                      className={`p-1.5 ${p.name === "default" ? "text-gray-200 dark:text-gray-600 cursor-not-allowed" : "text-gray-400 hover:text-red-500"}`}
                      title={p.name === "default" ? "Cannot delete default profile" : "Delete"}
                      disabled={p.name === "default"}
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  </>
                )}
              </div>
            </div>
            <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
              {p.schema === "slurm" ? `${p.user || ""}${p.user && p.host ? "@" : ""}${p.host || ""}` : "localhost"}
            </p>
          </div>
        ))}
      </div>

    </div>
  );
}

function HuggingFaceSection() {
  const [status, setStatus] = useState({ configured: false, username: null });
  const [isEditing, setIsEditing] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmSignOut, setConfirmSignOut] = useState(false);
  const { showError, showSuccess } = useNotification();

  // Fetch token status on mount
  useEffect(() => {
    // Use mock data in development mode
    if (import.meta.env.DEV) {
      setStatus({
        configured: true,
        username: "shamu",
        fullname: "Shamu the Orca",
        email: "shamu@seaworld.example",
        avatar_url: "https://huggingface.co/avatars/default.svg",
        token_name: "fish-finder-9000",
        token_role: "write",
        token_created_at: "2024-02-14T09:00:00Z",
      });
      setLoading(false);
      return;
    }

    fetchHfTokenStatus()
      .then(setStatus)
      .catch(() => setStatus({ configured: false }))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setSaving(true);

    // In dev mode, just set mock data
    if (import.meta.env.DEV) {
      setStatus({
        configured: true,
        username: "shamu",
        fullname: "Shamu the Orca",
        email: "shamu@seaworld.example",
        avatar_url: "https://huggingface.co/avatars/default.svg",
        token_name: "fish-finder-9000",
        token_role: "write",
        token_created_at: "2024-02-14T09:00:00Z",
      });
      setIsEditing(false);
      setInputValue("");
      setSaving(false);
      showSuccess("Signed in to Hugging Face");
      return;
    }

    try {
      const result = await setHfToken(inputValue);
      setStatus(result);
      setIsEditing(false);
      setInputValue("");
      showSuccess("Signed in to Hugging Face");
    } catch (err) {
      showError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleClear = async () => {
    // In dev mode, just update local state
    if (import.meta.env.DEV) {
      setStatus({ configured: false, username: null });
      setConfirmSignOut(false);
      showSuccess("Signed out of Hugging Face");
      return;
    }

    try {
      await deleteHfToken();
      setStatus({ configured: false, username: null });
      setConfirmSignOut(false);
      showSuccess("Signed out of Hugging Face");
    } catch (err) {
      showError(err.message);
    }
  };

  const renderHeader = () => (
    <div className="flex items-center justify-between mb-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
        Hugging Face
      </h3>
      {!status.configured && !isEditing && !loading && (
        <button
          onClick={() => setIsEditing(true)}
          className="rounded-md bg-blue-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600"
        >
          Sign In
        </button>
      )}
    </div>
  );

  if (loading) {
    return (
      <div>
        {renderHeader()}
        <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 border border-gray-200 dark:border-gray-600 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-600" />
            <div className="flex-1">
              <div className="h-4 w-24 bg-gray-200 dark:bg-gray-600 rounded" />
              <div className="mt-1.5 h-3 w-32 bg-gray-200 dark:bg-gray-600 rounded" />
            </div>
            <div className="h-8 w-20 bg-gray-200 dark:bg-gray-600 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (isEditing) {
    return (
      <div>
        {renderHeader()}
        <div className="space-y-3">
          <input
            type="password"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="hf_..."
            className="block w-full rounded-md border-0 py-1.5 px-3 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 focus:ring-2 focus:ring-inset focus:ring-blue-500 sm:text-sm sm:leading-6"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={!inputValue || saving}
              className="rounded-md bg-blue-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600 disabled:opacity-50"
            >
              {saving ? "Signing in..." : "Sign In"}
            </button>
            <button
              onClick={() => {
                setIsEditing(false);
                setInputValue("");
              }}
              className="px-3 py-1.5 text-sm font-medium text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!status.configured) {
    return <div>{renderHeader()}</div>;
  }

  return (
    <div>
      {renderHeader()}
      <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3 space-y-2 text-sm border border-gray-200 dark:border-gray-600">
        {/* User info */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {status.avatar_url && (
              <img
                src={status.avatar_url}
                alt=""
                className="h-10 w-10 rounded-full bg-gray-200 dark:bg-gray-600"
              />
            )}
            <div>
              <span className="text-gray-900 dark:text-white font-medium">
                {status.fullname || status.username}
              </span>
              {status.email && (
                <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{status.email}</p>
              )}
            </div>
          </div>
          {confirmSignOut ? (
            <div className="flex items-center gap-1">
              <button
                onClick={() => setConfirmSignOut(false)}
                className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                title="Cancel"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
              <button
                onClick={handleClear}
                className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
              >
                Confirm?
              </button>
            </div>
          ) : (
            <button
              onClick={() => setConfirmSignOut(true)}
              className="rounded-md bg-blue-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-600"
            >
              Sign Out
            </button>
          )}
        </div>
        {/* Token info */}
        {(status.token_name || status.token_role) && (
          <div className="pt-2 border-t border-gray-200 dark:border-gray-600">
            <div className="flex items-start justify-between">
              <div>
                <span className="text-blue-500 dark:text-blue-400 font-medium">Token</span>
                <p className="text-gray-500 dark:text-gray-400">{status.token_name || "unnamed"}</p>
                {status.token_created_at && (
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                    Created at {new Date(status.token_created_at).toLocaleString()}
                  </p>
                )}
              </div>
              {status.token_role && (
                <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${
                  status.token_role === "write"
                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                }`}>
                  {status.token_role}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function AppConfigSection() {
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Use mock data in development mode
    if (import.meta.env.DEV) {
      setInfo({
        HOST: "orca-pod.ocean.local",
        PORT: 8000,
        HOME_DIR: "/deep/blue/sea/.blackfish",
        DEBUG: true,
        CONTAINER_PROVIDER: "docker",
        VERSION: "1.0.0a2-whale",
      });
      setLoading(false);
      return;
    }

    fetchAppInfo()
      .then(setInfo)
      .catch(() => setInfo(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-2 animate-pulse">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex justify-between">
            <div className="h-4 w-28 bg-gray-200 dark:bg-gray-700 rounded" />
            <div className="h-4 w-36 bg-gray-200 dark:bg-gray-700 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const apiUrl = info ? `http://${info.HOST}:${info.PORT}` : blackfishApiURL;

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-700 dark:text-gray-300 font-medium">URL</span>
        <span className="text-gray-500 dark:text-gray-400 font-light">{apiUrl}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-700 dark:text-gray-300 font-medium">Home Directory</span>
        <span className="text-gray-500 dark:text-gray-400 font-light">{info?.HOME_DIR || "-"}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-700 dark:text-gray-300 font-medium">Debug</span>
        <span className="text-gray-500 dark:text-gray-400 font-light">{info?.DEBUG ? "Yes" : "No"}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-700 dark:text-gray-300 font-medium">Container Provider</span>
        <span className="text-gray-500 dark:text-gray-400 font-light">{info?.CONTAINER_PROVIDER || "-"}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-700 dark:text-gray-300 font-medium">Version</span>
        <span className="text-gray-500 dark:text-gray-400 font-light">{info?.VERSION || "-"}</span>
      </div>
    </div>
  );
}

function SettingsSlideOver() {
  const { isOpen, closeSettings } = useSettings();
  const [notification, setNotification] = useState({ show: false, variant: "error", message: "" });

  // Auto-dismiss notification after 5 seconds
  useEffect(() => {
    if (notification.show) {
      const timer = setTimeout(() => {
        setNotification((prev) => ({ ...prev, show: false }));
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [notification.show]);

  const showError = (message) => {
    setNotification({ show: true, variant: "error", message });
  };

  const showSuccess = (message) => {
    setNotification({ show: true, variant: "success", message });
  };

  return (
    <NotificationContext.Provider value={{ showError, showSuccess }}>
      <Dialog open={isOpen} onClose={closeSettings} className="relative z-50">
      <DialogBackdrop
        transition
        className="fixed inset-0 bg-gray-500 dark:bg-gray-900 bg-opacity-75 dark:bg-opacity-80 transition-opacity duration-300 ease-linear data-[closed]:opacity-0"
      />
      <div className="fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 overflow-hidden">
          <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
            <DialogPanel
              transition
              className="pointer-events-auto w-screen max-w-md transform transition duration-300 ease-in-out data-[closed]:translate-x-full"
            >
              <div className="flex h-full flex-col overflow-y-scroll bg-white dark:bg-gray-800 shadow-2xl ring-1 ring-gray-900/10 dark:ring-white/10">
                {/* Header */}
                <div className="px-4 py-4 sm:px-6 border-b border-gray-200 dark:border-gray-700">
                  <div className="flex items-center justify-between">
                    <DialogTitle className="text-lg font-semibold text-gray-900 dark:text-white">
                      Settings
                    </DialogTitle>
                    <TransitionChild>
                      <button
                        type="button"
                        onClick={closeSettings}
                        className="rounded-md text-gray-400 hover:text-gray-500 dark:hover:text-gray-300 focus:outline-none data-[closed]:opacity-0"
                      >
                        <span className="sr-only">Close panel</span>
                        <XMarkIcon className="h-6 w-6" />
                      </button>
                    </TransitionChild>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 px-4 py-6 sm:px-6 space-y-8">
                  {/* Profiles Section */}
                  <section>
                    <ProfilesSection />
                  </section>

                  {/* Hugging Face Section */}
                  <section>
                    <HuggingFaceSection />
                  </section>

                  {/* App Configuration Section */}
                  <section>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                      App Configuration
                    </h3>
                    <AppConfigSection />
                  </section>

                  {/* Theme Section */}
                  <section>
                    <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
                      Theme
                    </h3>
                    <ThemeSelector />
                  </section>
                </div>
              </div>
            </DialogPanel>
          </div>
        </div>
      </div>
    </Dialog>
      <Notification
        show={notification.show}
        variant={notification.variant}
        message={notification.message}
        onDismiss={() => setNotification((prev) => ({ ...prev, show: false }))}
      />
    </NotificationContext.Provider>
  );
}

export default SettingsSlideOver;
