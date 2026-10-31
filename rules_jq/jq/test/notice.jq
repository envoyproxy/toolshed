import "greet" as greet;
import "renamed/feature" as feature;
import "absolute/helper" as absolute;
import "config" as $config;
import "generated" as generated;
{
  greeting: (" world " | greet::hello),
  remapped: feature::value,
  absolute: absolute::value,
  config: $config[0].value,
  answer: generated::answer
}
