import re
from typing import TYPE_CHECKING, Any, List, Mapping, NamedTuple, Optional, Sequence, TypeVar, Union

import dagster._check as check
import dagster._seven as seven
from dagster._annotations import PublicAttr
from dagster._serdes import whitelist_for_serdes

ASSET_KEY_SPLIT_REGEX = re.compile("[^a-zA-Z0-9_]")
ASSET_KEY_DELIMITER = "/"

if TYPE_CHECKING:
    from dagster._core.definitions.assets import AssetsDefinition
    from dagster._core.definitions.source_asset import SourceAsset


def parse_asset_key_string(s: str) -> Sequence[str]:
    return list(filter(lambda x: x, re.split(ASSET_KEY_SPLIT_REGEX, s)))


@whitelist_for_serdes
class AssetKey(NamedTuple("_AssetKey", [("path", PublicAttr[Sequence[str]])])):
    """Object representing the structure of an asset key.  Takes in a sanitized string, list of
    strings, or tuple of strings.

    Example usage:

    .. code-block:: python

        from dagster import AssetKey

        AssetKey("asset1")
        AssetKey(["asset1"]) # same as the above
        AssetKey(["prefix", "asset1"])
        AssetKey(["prefix", "subprefix", "asset1"])

    Args:
        path (Union[str, Sequence[str]]): String, list of strings, or tuple of strings.  A list of
            strings represent the hierarchical structure of the asset_key.
    """

    def __new__(cls, path: Union[str, Sequence[str]]):
        if isinstance(path, str):
            path = [path]
        else:
            path = list(check.sequence_param(path, "path", of_type=str))

        return super(AssetKey, cls).__new__(cls, path=path)

    def __str__(self):
        return f"AssetKey({self.path})"

    def __repr__(self):
        return f"AssetKey({self.path})"

    def __hash__(self):
        return hash(tuple(self.path))

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return False

        return self.path == other.path

    def to_string(self) -> str:
        """E.g. '["first_component", "second_component"]'."""
        return self.to_db_string()

    def to_db_string(self) -> str:
        return seven.json.dumps(self.path)

    def to_user_string(self) -> str:
        """E.g. "first_component/second_component"."""
        return ASSET_KEY_DELIMITER.join(self.path)

    def to_python_identifier(self, suffix: Optional[str] = None) -> str:
        """Build a valid Python identifier based on the asset key that can be used for
        operation names or I/O manager keys.
        """
        path = list(self.path)

        if suffix is not None:
            path.append(suffix)

        return "__".join(path).replace("-", "_")

    @staticmethod
    def from_user_string(asset_key_string: str) -> "AssetKey":
        return AssetKey(asset_key_string.split(ASSET_KEY_DELIMITER))

    @staticmethod
    def from_db_string(asset_key_string: Optional[str]) -> Optional["AssetKey"]:
        if not asset_key_string:
            return None
        if asset_key_string[0] == "[":
            # is a json string
            try:
                path = seven.json.loads(asset_key_string)
            except seven.JSONDecodeError:
                path = parse_asset_key_string(asset_key_string)
        else:
            path = parse_asset_key_string(asset_key_string)
        return AssetKey(path)

    @staticmethod
    def get_db_prefix(path: Sequence[str]):
        check.sequence_param(path, "path", of_type=str)
        return seven.json.dumps(path)[:-2]  # strip trailing '"]' from json string

    @staticmethod
    def from_graphql_input(graphql_input_asset_key: Mapping[str, Sequence[str]]) -> "AssetKey":
        return AssetKey(graphql_input_asset_key["path"])

    def to_graphql_input(self) -> Mapping[str, Sequence[str]]:
        return {"path": self.path}

    @staticmethod
    def from_coercible(arg: "CoercibleToAssetKey") -> "AssetKey":
        if isinstance(arg, AssetKey):
            return check.inst_param(arg, "arg", AssetKey)
        elif isinstance(arg, str):
            return AssetKey([arg])
        elif isinstance(arg, list):
            check.list_param(arg, "arg", of_type=str)
            return AssetKey(arg)
        elif isinstance(arg, tuple):
            check.tuple_param(arg, "arg", of_type=str)
            return AssetKey(arg)
        else:
            check.failed(f"Unexpected type for AssetKey: {type(arg)}")

    @staticmethod
    def from_coercible_or_definition(
        arg: Union["CoercibleToAssetKey", "AssetsDefinition", "SourceAsset"],
    ) -> "AssetKey":
        from dagster._core.definitions.assets import AssetsDefinition
        from dagster._core.definitions.source_asset import SourceAsset

        if isinstance(arg, AssetsDefinition):
            return arg.key
        elif isinstance(arg, SourceAsset):
            return arg.key
        else:
            return AssetKey.from_coercible(arg)

    def has_prefix(self, prefix: Sequence[str]) -> bool:
        return len(self.path) >= len(prefix) and self.path[: len(prefix)] == prefix

    def with_prefix(self, prefix: "CoercibleToAssetKeyPrefix") -> "AssetKey":
        prefix = key_prefix_from_coercible(prefix)
        return AssetKey(list(prefix) + list(self.path))


CoercibleToAssetKey = Union[AssetKey, str, Sequence[str]]
CoercibleToAssetKeyPrefix = Union[str, Sequence[str]]


def check_opt_coercible_to_asset_key_prefix_param(
    prefix: Optional[CoercibleToAssetKeyPrefix], param_name: str
) -> Optional[Sequence[str]]:
    try:
        return key_prefix_from_coercible(prefix) if prefix is not None else None
    except check.CheckError:
        raise check.ParameterCheckError(
            f'Param "{param_name}" is not a string or a sequence of strings'
        )


def key_prefix_from_coercible(key_prefix: CoercibleToAssetKeyPrefix) -> Sequence[str]:
    if isinstance(key_prefix, str):
        return [key_prefix]
    elif isinstance(key_prefix, list):
        return key_prefix
    else:
        check.failed(f"Unexpected type for key_prefix: {type(key_prefix)}")


@whitelist_for_serdes(old_storage_names={"AssetCheckHandle"})
class AssetCheckKey(NamedTuple):
    """Check names are expected to be unique per-asset. Thus, this combination of asset key and
    check name uniquely identifies an asset check within a deployment.
    """

    asset_key: PublicAttr[AssetKey]
    name: PublicAttr[str]

    @staticmethod
    def from_graphql_input(graphql_input: Mapping[str, Any]) -> "AssetCheckKey":
        return AssetCheckKey(
            asset_key=AssetKey.from_graphql_input(graphql_input["assetKey"]),
            name=graphql_input["name"],
        )

    def to_user_string(self) -> str:
        return f"{self.asset_key.to_user_string()}:{self.name}"

    @staticmethod
    def from_user_string(user_string: str) -> "AssetCheckKey":
        asset_key_str, name = user_string.split(":")
        return AssetCheckKey(AssetKey.from_user_string(asset_key_str), name)

    @staticmethod
    def from_db_string(db_string: str) -> Optional["AssetCheckKey"]:
        try:
            values = seven.json.loads(db_string)
            if isinstance(values, dict) and values.keys() == {"asset_key", "check_name"}:
                return AssetCheckKey(
                    asset_key=check.not_none(AssetKey.from_db_string(values["asset_key"])),
                    name=check.inst(values["check_name"], str),
                )
            else:
                return None
        except seven.JSONDecodeError:
            return None

    def to_db_string(self) -> str:
        return seven.json.dumps({"asset_key": self.asset_key.to_string(), "check_name": self.name})


EntityKey = Union[AssetKey, AssetCheckKey]
T_EntityKey = TypeVar("T_EntityKey", AssetKey, AssetCheckKey, EntityKey)


def entity_key_from_db_string(db_string: str) -> EntityKey:
    check_key = AssetCheckKey.from_db_string(db_string)
    return check_key if check_key else check.not_none(AssetKey.from_db_string(db_string))


def asset_keys_from_defs_and_coercibles(
    assets: Sequence[Union["AssetsDefinition", CoercibleToAssetKey]],
) -> Sequence[AssetKey]:
    from dagster._core.definitions.assets import AssetsDefinition

    result: List[AssetKey] = []
    for el in assets:
        if isinstance(el, AssetsDefinition):
            result.extend(el.keys)
        else:
            result.append(
                AssetKey.from_user_string(el)
                if isinstance(el, str)
                else AssetKey.from_coercible(el)
            )
    return result
