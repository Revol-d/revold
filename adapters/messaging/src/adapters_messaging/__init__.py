"""Adapters de mensageria (filas/eventos entre cores). PENDENTE — hoje nenhum
core além de catalog está implementado, então ainda não há evento real para
transportar. Ver contracts/events/ para onde os schemas de evento devem viver
quando o primeiro evento entre cores for definido (provável candidato:
CartCheckedOut, publicado por core-cart e consumido por core-notification)."""
