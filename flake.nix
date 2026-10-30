{
  description = "Dev environment for Dapla Lab helm-charts";

  inputs = {
    flake-parts.url = "github:hercules-ci/flake-parts";
    nixpkgs.url = "https://channels.nixos.org/nixpkgs-unstable/nixexprs.tar.zst";
  };

  outputs = inputs @ {flake-parts, ...}:
    flake-parts.lib.mkFlake {inherit inputs;} {
      systems = ["x86_64-linux" "aarch64-linux" "aarch64-darwin"];
      perSystem = {
        pkgs,
        ...
      }: {
        devShells.default = pkgs.mkShell {
          name = "Dapla Lab helm charts";
          packages = with pkgs; [
            cljfmt
            clj-kondo
            clojure-lsp
            babashka
            nixd
            ruff
            uv
            vscode-langservers-extracted
            yaml-language-server
            kubernetes-helm
          ];
        };

        formatter = pkgs.alejandra;
      };
    };
}
