let
  nixpkgs = fetchTarball "https://github.com/NixOS/nixpkgs/tarball/nixpkgs-unstable";
  pkgs = import nixpkgs {};
  HERE = builtins.toString ./.;
in

pkgs.mkShellNoCC {
  packages = builtins.attrValues {
      inherit (pkgs)
        ffmpeg
        ;

      python3 = pkgs.python3.withPackages (p: builtins.attrValues {
        inherit (p)
          beautifulsoup4
          mutagen
          mypy
          pydantic
          pyyaml
          requests
          rich
          types-pyyaml
          types-requests
          yt-dlp
          ;
      });

      lyrebird = pkgs.writeScriptBin "lyrebird" ''
        #!/bin/sh
        exec python3 -m lyrebird "$@"
      '';
  };

  PYTHONPATH = HERE;
}
