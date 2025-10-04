let
  pkgs = import <nixpkgs> {};
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
          pydantic
          pyyaml
          requests
          yt-dlp
          ;
      });
  };

  PYTHONPATH = HERE;
}
