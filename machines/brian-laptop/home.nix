# Laptop home-manager configuration
{ config, pkgs, ... }:

{
  home.homeDirectory = "/home/brian";
  home.stateVersion = "25.05";
  programs.home-manager.enable = true;

  # Shell configuration
  programs.bash = {
    enable = true;
    bashrcExtra = ''
      # Custom bash configuration for laptop
      export EDITOR=vim
      alias ls="ls --color=auto"
      alias ll="ls -lh"
      alias battery="upower -e | grep BAT"
    '';
  };

  # Git configuration
  programs.git = {
    enable = true;
    userName = "Your Name";
    userEmail = "you@example.com";
    extraConfig = {
      core.editor = "vim";
      pull.rebase = true;
    };
  };

  # Vim configuration
  programs.vim = {
    enable = true;
    settings = {
      number = true;
      tabstop = 4;
      shiftwidth = 4;
    };
  };

  # Home packages
  home.packages = with pkgs; [
    neofetch
    ripgrep
    fd
    acpi
  ];
}
